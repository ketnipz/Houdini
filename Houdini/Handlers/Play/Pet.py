import time, random

from Houdini.Handlers import Handlers, XT
from Houdini.Data.Puffle import Puffle
from Houdini.Data.Mail import Mail

puffleStatistics = {
    0: (100, 100, 100),
    1: (100, 120, 80),
    2: (120, 80, 100),
    3: (80, 100, 120),
    4: (80, 120, 80),
    5: (100, 80, 120),
    6: (100, 100, 100),
    7: (120, 80, 100),
    8: (100, 80, 120)
}

@Handlers.Handle(XT.GetPlayerPuffles)
def handleGetPuffles(self, data):
    ownedPuffles = self.session.query(Puffle).filter(Puffle.Owner == data.PlayerId)

    playerPuffles = ["%d|%s|%d|%d|%d|%d|100|100|100|0|0|%d" % (puffle.ID, puffle.Name, puffle.Type, puffle.Health,
                                                               puffle.Hunger, puffle.Rest, puffle.Walking)
                     for puffle in ownedPuffles]

    playerPufflesString = "%".join(playerPuffles)

    self.sendXt("pg", playerPufflesString)

@Handlers.Handle(XT.GetMyPlayerPuffles)
def handleGetMyPlayerPuffles(self, data):
    ownedPuffles = self.session.query(Puffle).filter(Puffle.Owner == self.user.ID)

    for ownedPuffle in ownedPuffles:
        self.puffles[ownedPuffle.ID] = ownedPuffle

    playerPuffles = ["%d|%s|%d|%d|%d|%d|100|100|100" % (puffle.ID, puffle.Name, puffle.Type, puffle.Health,
                                                        puffle.Hunger, puffle.Rest)
                     for puffle in ownedPuffles]

    myPufflesString = "%".join(playerPuffles)

    self.sendXt("pgu", myPufflesString)

@Handlers.Handle(XT.AdoptPuffle)
def handleSendAdoptPuffle(self, data):
    if not data.TypeId in puffleStatistics:
        return self.transport.loseConnection()

    if self.user.Coins < 800:
        return self.sendError(401)
    
    if len(data.Name) < 1 or len(data.Name) > 25:
        return self.sendError(441)
    
    self.user.Coins -= 800

    maxHealth, maxHunger, maxRest = puffleStatistics[data.TypeId]

    adoptionDate = time.time()

    puffle = Puffle(Owner=self.user.ID, Name=data.Name, AdoptionDate=adoptionDate, Type=data.TypeId,
                    Health=maxHunger, Hunger=maxHunger, Rest=maxRest)
    self.session.add(puffle)
    self.session.commit()

    puffleString = "%d|%s|%d|100|100|100|100|100|100" % (puffle.ID, data.Name, data.TypeId)
    self.sendXt("pn", self.user.Coins, puffleString)

    postcard = Mail(Recipient=self.user.ID, SenderName="sys",
                    SenderID=0, Details=data.Name, Date=adoptionDate,
                    Type=111)
    self.session.add(postcard)
    self.session.commit()

    self.sendXt("mr", "sys", 0, 111, data.Name, adoptionDate, postcard.ID)

    # Refresh my player puffles
    handleGetMyPlayerPuffles(self, [])

@Handlers.Handle(XT.MovePuffle)
def handleSendPuffleMove(self, data):
    if data.PuffleId in self.puffles:
        self.room.sendXt("pm", data.PuffleId, data.X, data.Y)

@Handlers.Handle(XT.WalkPuffle)
def handleSendPuffleWalk(self, data):
    if data.PuffleId in self.puffles:
        puffle = self.puffles[data.PuffleId]
        if puffle.Rest < 20 and puffle.Hunger < 40:
            return # Client shouldn't have been allowed to send this packet

        puffle.Walking = 1 if not puffle.Walking else 0

        self.session.add(puffle)
        self.session.commit()

        # Blame Club Penguin and not me!
        puffleData = [data.PuffleId]
        puffleData[1:11] = [''] * 11
        puffleData.append(puffle.Walking)

        puffleString = "|".join([str(puffleElement) for puffleElement in puffleData])

        self.room.sendXt("pw", self.user.ID, puffleString)

@Handlers.Handle(XT.PlayPuffle)
def handleSendPufflePlay(self, data):
    if data.PuffleId in self.puffles:
        puffle = self.puffles[data.PuffleId]

        if puffle.Rest < 20 or puffle.Health < 10:
            return  # Client shouldn't have been allowed to send this packet

        maxHealth, maxHunger, maxRest = puffleStatistics[puffle.Type]

        negativeHunger = random.randrange(10, 25)
        negativeRest = random.randrange(10, 25)

        puffle.Hunger = max(0, min(puffle.Hunger - negativeHunger, maxHunger))
        puffle.Rest = max(0, min(puffle.Rest - negativeRest, maxRest))

        maxStatistic = max(puffle.Hunger, puffle.Rest)
        minStatistic = min(puffle.Hunger, puffle.Rest)
        puffle.Health = random.randrange(minStatistic, maxStatistic)

        playType = 1 if puffle.Rest > 80 else random.choice([0, 2])

        playString = "%d|Hou|dini|%d|%d|%d" % (puffle.ID, puffle.Health, puffle.Hunger, puffle.Rest)

        self.room.sendXt("pp", playString, playType)

@Handlers.Handle(XT.RestPuffle)
def handleSendPuffleRest(self, data):
    if data.PuffleId in self.puffles:
        puffle = self.puffles[data.PuffleId]

        maxHealth, maxHunger, maxRest = puffleStatistics[puffle.Type]

        additionalHunger = random.randrange(5, 25)
        additionalRest = random.randrange(10, 25)

        puffle.Hunger = max(0, min(puffle.Hunger + additionalHunger, maxHunger))
        puffle.Rest = max(0, min(puffle.Rest + additionalRest, maxRest))

        maxStatistic = max(puffle.Hunger, puffle.Rest)
        minStatistic = min(puffle.Hunger, puffle.Rest)
        puffle.Health = random.randrange(minStatistic, maxStatistic)

        restString = "%d|Hou|dini|%d|%d|%d" % (puffle.ID, puffle.Health, puffle.Hunger, puffle.Rest)

        self.room.sendXt("pr", restString)

# TODO: Consider writing reusable functions for these handlers..?
@Handlers.Handle(XT.TreatPuffle)
def handleSendPuffleTreat(self, data):
    if data.PuffleId in self.puffles:
        puffle = self.puffles[data.PuffleId]

        maxHealth, maxHunger, maxRest = puffleStatistics[puffle.Type]

        additionalHunger = random.randrange(5, 15)
        puffle.Hunger = max(0, min(puffle.Hunger + additionalHunger, maxHunger))

        self.user.Coins -= 5

        treatString = "%d|Hou|dini|%d|%d|%d" % (puffle.ID, puffle.Health, puffle.Hunger, puffle.Rest)

        self.room.sendXt("pt", self.user.Coins, treatString, data.TreatId)

@Handlers.Handle(XT.FeedPuffle)
def handleSendPuffleFood(self, data):
    if data.PuffleId in self.puffles:
        puffle = self.puffles[data.PuffleId]

        maxHealth, maxHunger, maxRest = puffleStatistics[puffle.Type]

        additionalHunger = random.randrange(5, 15)
        puffle.Hunger = max(0, min(puffle.Hunger + additionalHunger, maxHunger))

        self.user.Coins -= 10

        feedString = "%d|Hou|dini|%d|%d|%d" % (puffle.ID, puffle.Health, puffle.Hunger, puffle.Rest)

        self.room.sendXt("pf", self.user.Coins, feedString)

@Handlers.Handle(XT.BathPuffle)
def handleSendPuffleBath(self, data):
    if data.PuffleId in self.puffles:
        puffle = self.puffles[data.PuffleId]

        maxHealth, maxHunger, maxRest = puffleStatistics[puffle.Type]

        additionalRest = random.randrange(5, 15)
        puffle.Rest = max(0, min(puffle.Rest + additionalRest, maxRest))

        self.user.Coins -= 5

        bathString = "%d|Hou|dini|%d|%d|%d" % (puffle.ID, puffle.Health, puffle.Hunger, puffle.Rest)

        self.room.sendXt("pb", self.user.Coins, bathString)

@Handlers.Handle(XT.PuffleInitInteractionPlay)
def handleSendPuffleInitPlayInteraction(self, data):
    if data.PuffleId in self.puffles:
        self.room.sendXt("pip", data.PuffleId, data.X, data.Y)

@Handlers.Handle(XT.PuffleInitInteractionRest)
def handleSendPuffleInitRestInteraction(self, data):
    if data.PuffleId in self.puffles:
        self.room.sendXt("pir", data.PuffleId, data.X, data.Y)

@Handlers.Handle(XT.InteractionPlay)
def handleSendPlayInteraction(self, data):
    if data.PuffleId in self.puffles:
        puffle = self.puffles[data.PuffleId]

        if puffle.Rest < 20 or puffle.Health < 10:
            return  # Client shouldn't have been allowed to send this packet

        maxHealth, maxHunger, maxRest = puffleStatistics[puffle.Type]

        negativeHunger = random.randrange(10, 25)
        negativeRest = random.randrange(10, 25)

        puffle.Hunger = max(0, min(puffle.Hunger - negativeHunger, maxHunger))
        puffle.Rest = max(0, min(puffle.Rest - negativeRest, maxRest))

        maxStatistic = max(puffle.Hunger, puffle.Rest)
        minStatistic = min(puffle.Hunger, puffle.Rest)
        puffle.Health = random.randrange(minStatistic, maxStatistic)

        playString = "%d|Hou|dini|%d|%d|%d" % (puffle.ID, puffle.Health, puffle.Hunger, puffle.Rest)

        self.room.sendXt("ip", playString, data.X, data.Y)

@Handlers.Handle(XT.InteractionRest)
def handleSendRestInteraction(self, data):
    if data.PuffleId in self.puffles:
        puffle = self.puffles[data.PuffleId]

        maxHealth, maxHunger, maxRest = puffleStatistics[puffle.Type]

        additionalHunger = random.randrange(5, 25)
        additionalRest = random.randrange(10, 25)

        puffle.Hunger = max(0, min(puffle.Hunger + additionalHunger, maxHunger))
        puffle.Rest = max(0, min(puffle.Rest + additionalRest, maxRest))

        maxStatistic = max(puffle.Hunger, puffle.Rest)
        minStatistic = min(puffle.Hunger, puffle.Rest)
        puffle.Health = random.randrange(minStatistic, maxStatistic)

        restString = "%d|Hou|dini|%d|%d|%d" % (puffle.ID, puffle.Health, puffle.Hunger, puffle.Rest)

        self.room.sendXt("ir", restString, data.X, data.Y)

@Handlers.Handle(XT.InteractionFeed)
def handleSendFeedInteraction(self, data):
    if data.PuffleId in self.puffles:
        puffle = self.puffles[data.PuffleId]

        maxHealth, maxHunger, maxRest = puffleStatistics[puffle.Type]

        additionalHunger = random.randrange(5, 15)
        puffle.Hunger = max(0, min(puffle.Hunger + additionalHunger, maxHunger))

        self.user.Coins -= 10

        feedString = "%d|Hou|dini|%d|%d|%d" % (puffle.ID, puffle.Health, puffle.Hunger, puffle.Rest)

        self.room.sendXt("if", self.user.Coins, feedString, data.X, data.Y)

@Handlers.Handle(XT.PuffleFrame)
def handleSendPuffleFrame(self, data):
    if data.PuffleId in self.puffles:
        self.room.sendXt("ps", data.PuffleId, data.FrameId)
