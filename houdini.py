from Houdini.Houdini import Houdini

login = Houdini("houdini.conf", server="Login")
game = Houdini("houdini.conf", server="Wind")

login.start()
game.start()
