import os
from bot import MyLuxchatBot

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

conf_file = __location__+'/config.ini'

print("Loading Bot")
my_bot = MyLuxchatBot(conf_file)
print("Starting Bot")
my_bot.run()
print("Bot ended")
