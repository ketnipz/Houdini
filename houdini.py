from Houdini.Houdini import Houdini
from multiprocessing import Process

login_server = Process(target = Houdini, args=("houdini.conf",), kwargs={"server": "Login"})
game_server = Process(target = Houdini, args=("houdini.conf",), kwargs={"server": "Wind"})

game_server.start()
login_server.start()
