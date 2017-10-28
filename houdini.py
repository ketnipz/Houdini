from Houdini.Houdini import Houdini
from multiprocessing import Process

login = Houdini("houdini.conf", server="Login")
game = Houdini("houdini.conf", server="Wind")

game_server = Process(target = login.start())
login_server = Process(target = game.start())

game_server.start()
login_server.start()
