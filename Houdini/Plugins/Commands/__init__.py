import zope.interface, logging
from twisted.internet import reactor
from twisted.internet.threads import blockingCallFromThread, deferToThread

from Houdini.Plugins import Plugin
from Houdini.Handlers import Handlers
from Houdini.Data.Penguin import Penguin
from Houdini.Handlers.Play.Item import handleBuyInventory
from Houdini.Handlers.Play.Moderation import moderatorBan, moderatorKick
from Houdini.Handlers.Play.Igloo import handleBuyFurniture

commandCollection = {}

def Command(commandName, *commandArguments):
    def decoratorFunction(commandHandler):
        uppercaseCommand = commandName.upper()

        commandCollection[uppercaseCommand] = {
            "Handler": commandHandler,
            "Arguments": commandArguments
        }

        return commandHandler
    return decoratorFunction

class CommandArgument(object):

    def __init__(self, arbitraryName, argumentType):
        self.arbitraryName = arbitraryName
        self.argumentType = argumentType

class TokenizedArgument(CommandArgument):
    pass

class VariableCommandArgument(object):

    def __init__(self, arbitraryName):
        self.arbitraryName = arbitraryName

class Commands(object):
    zope.interface.implements(Plugin)

    author = "Houdini Team"
    version = 0.1
    description = "A commands plugin"

    commandPrefix = "!"
    tokenizedDelimiter = " / "

    coinLimit = 1000000

    commands = {}

    def __init__(self, server):
        self.logger = logging.getLogger("Houdini")

        self.server = server

        self.bot = self.server.plugins["Bot"]

        Handlers.Message += self.handleMessage

    @staticmethod
    def getPlayer(sessionObject, playerUsername, specificQuery=Penguin):
        player = sessionObject.query(specificQuery). \
            filter_by(Username=playerUsername).scalar()

        return player

    def botRandomize(self, player, arguments):
        if player.user.Moderator:
            self.logger.debug("Bot randomization command used by {}".format(player.user.Username))

            self.bot.randomizeClothing()
            self.bot.randomizeName()
            self.bot.updateString()
            reactor.callFromThread(self.bot.removeFromRoom, player)
            reactor.callFromThread(self.bot.addToRoom, player)

    def botAnnounce(self, player, arguments):
        if player.user.Moderator:
            announcementMessage = " ".join(arguments)

            for otherPlayer in self.server.players.values():
                self.bot.sendMessage(otherPlayer, announcementMessage)

    @Command("bot", VariableCommandArgument("Action"))
    def handleBotCommand(self, player, arguments):
        if player.user.Moderator:
            subCommand = arguments.Action[0].lower().title()

            commandMethod = getattr(self, "bot" + subCommand, lambda x, y: "Invalid sub-command.")
            if not commandMethod:
                return

            commandMethod(player, arguments.Action[1:])

    @Command("kick", VariableCommandArgument("Username"))
    def handleKickCommand(self, player, arguments):
        if player.user.Moderator:
            playerId = blockingCallFromThread(reactor, self.getPlayer, player.session,
                                              arguments.Username, Penguin.ID)

            if playerId is not None and playerId in self.server.players:
                if not self.server.players[playerId].user.Moderator:
                    reactor.callFromThread(moderatorKick, player, playerId)

                    self.logger.info("%s has kicked %s" % (player.user.Username, arguments.Username))

    # Example: !BAN King Arthur / 24 / Not actually king.
    @Command("ban", TokenizedArgument("Username", str),
             TokenizedArgument("Duration", int),
             TokenizedArgument("Reason", str))
    def handleBanCommand(self, player, arguments):
        if player.user.Moderator:
            self.logger.info("%s is attempting to ban %s." % (player.user.Username, arguments.Username))

            playerId = blockingCallFromThread(reactor, self.getPlayer, player.session,
                                              arguments.Username, Penguin.ID)

            if playerId is not None:
                reactor.callFromThread(moderatorBan, player, playerId,
                                       arguments.Duration, arguments.Reason)

                self.logger.info("%s has banned %s for %s hours using the !BAN command." %
                                 (player.user.Username, arguments.Username, arguments.Duration))

    @Command("jr", CommandArgument("RoomId", int))
    def handleJoinRoomCommand(self, player, arguments):
        if arguments.RoomId in self.server.rooms:
            player.x = 0
            player.y = 0
            player.frame = 1

            reactor.callFromThread(player.joinRoom, arguments.RoomId)

            if self.bot.isStationary:
                reactor.callFromThread(self.bot.addToRoom, player)

    @Command("ac", CommandArgument("Coins", int))
    def handleCoinsCommand(self, player, arguments):
        self.logger.debug("%s is trying to add %d coins" % (player.user.Username, arguments.Coins))

        newAmount = max(min(self.coinLimit, player.user.Coins + arguments.Coins), 1)

        reactor.callFromThread(player.sendCoins, newAmount)

    @Command("ai", CommandArgument("ItemId", int))
    def handleItemCommand(self, player, arguments):
        self.logger.debug("%s is trying to add an item (id: %d)" % (player.user.Username, arguments.ItemId))

        if not self.server.items.isBait(arguments.ItemId):
            reactor.callFromThread(handleBuyInventory, player, arguments)

    @Command("af", CommandArgument("FurnitureId", int))
    def handleFurnitureCommand(self, player, arguments):
                self.logger.debug("%s is trying to add an item (id: %d)" % (player.user.Username, arguments.FurnitureId))

                reactor.callFromThread(handleBuyFurniture, player, arguments)

    @Command("ping")
    def handlePingCommand(self, player, arguments):
        self.logger.debug("Received ping command from %s" % player.user.Username)

        self.bot.sendMessage(player, "Pong!")

    # Do not edit below this line.
    def processCommand(self, messageDetails):
        playerObject, commandMessage = messageDetails

        commandTokens = commandMessage.split(" ")
        commandString = commandTokens.pop(0).upper()

        if commandString not in commandCollection:
            return  # Command doesn't exist!

        commandArguments = commandCollection[commandString]["Arguments"]
        commandHandler = commandCollection[commandString]["Handler"]

        if not commandArguments:
            return commandHandler(self, playerObject, None)

        # Better way to do this?
        if isinstance(commandArguments[0], TokenizedArgument):
            commandTokens = commandMessage.split(" ")[1:] # Remove the command itself
            commandTokens = " ".join(commandTokens).split(self.tokenizedDelimiter) # Rejoin and split by the delimiter

        commandData = CommandData()
        tokenIndex = 0
        for commandToken in commandTokens:
            commandArgument = commandArguments[tokenIndex]

            if not isinstance(commandArgument, VariableCommandArgument):
                if commandArgument.argumentType is int:
                    if not commandToken.isdigit():
                        raise Exception("%r had an invalid argument" % commandString)

                    setattr(commandData, commandArgument.arbitraryName, int(commandTokens[tokenIndex]))

                else:
                    if commandArgument.argumentType is not str:
                        raise Exception("%r had an invalid argument" % commandString)

                    setattr(commandData, commandArgument.arbitraryName, str(commandTokens[tokenIndex]))
            else:
                setattr(commandData, commandArgument.arbitraryName, commandTokens[tokenIndex:])
                break

            tokenIndex += 1

            if tokenIndex > len(commandArguments) - 1:
                break

        return commandHandler(self, playerObject, commandData)

    def handleCommandError(self, error):
        self.logger.error(error)

    def handleMessage(self, player, data):
        self.logger.info("[Commands] Received message from %s: '%s'" % (player.user.Username, data.Message))

        if data.Message.startswith(self.commandPrefix):
            commandMessage = data.Message[1:]

            deferToThread(self.processCommand, [player, commandMessage])\
                .addErrback(self.handleCommandError)

    def ready(self):
        self.logger.info("Commands plugin has been loaded!")

class CommandData:
    pass


