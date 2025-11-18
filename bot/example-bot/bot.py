#Default imports
import os
import glob
import time
import sys
import asyncio
import niobot
from flask import request, jsonify

#Only needed if using docker
sys.path.append("./luxchatbot")

#Luxchatbot imports here
from luxchatbot import LuxchatBot
from api import LuxchatApi

class MyLuxchatApi(LuxchatApi):
    """
    A custom implementation of the LuxchatApi.

    You can override certain functions to implement your own API behavior
    """

    def add_custom_endpoints(self):
        """
        add_custom_endpoints contains the definitions of your API (flask) endpoints

        Define your own API endpoints here
        """

        @self.api.route('/send_message', methods=['POST'])
        def send_message():
            """
            An example endpoint that sends a message to a given room
            """
            data = request.json
            result = self.send_to_bot(message=data['message'], room_id=data['room_id'])

            return jsonify({"message": result['message']}), result['code']


class MyLuxchatBot(LuxchatBot):
    """
    A custom implementation of the LuxchatBot

    Below are some functions you can override to implement your own behaviour.
    """

    def get_required_config_values(self):
        required_values = super().get_required_config_values()

        required_values["openweatherapi"] = {
            "api_key" : None,
        }

        return required_values

    def pre_setup(self):
        """
        This function is called before the startup of the bot, useful for defining the classes to use to initialize the API or the bot.
        """

        # This overrides the default LuxchatApi with the custom one defined above
        self.apiclass = MyLuxchatApi

    def custom_setup(self):
        """
        This function is called during startup of the bot

        We will use it to override the built-in API by our Custom API defined above
        """
        # Load custom commands in modules folder
        path = os.path.dirname(__file__)
        modules = glob.glob(f'{path}/modules/*.py')
        for f in modules:
            (mod, p) = os.path.basename(f).split(".")
            self.bot.mount_module(f'modules.{mod}')

        # Modify the default looper sleep time (Default is 10s)
        self.looper_sleep = 5
        # Keep a variable to count loops
        self.custom_counter = 0


    async def custom_looper(self):
        """
        The looper is a built in loop function that is started with the bot.

        This function is called continuously with a delay between calls.
        You can use this to make the bot perform recurring actions
        """

        room_id = self.config.get('config', 'management_room')
        start = self.tstamp['init_start']
        uptime = time.time() - start
        msg = f"Loop {self.custom_counter} - This Bot has been running for {uptime:.3f} seconds"
        self.custom_counter += 1
        await self.bot.send_message(room_id, content = msg)