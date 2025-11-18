# Luxchat Bot System

This README is a work in progress and currently only contains the bare basics to get a bot running.

## Requirements

- You must have a user account on the target system and configure it as owner_id in the bot's config.ini
- You must have a bot account on the server you want to run the bot on
- Ideally you must be able to log in to the bot account manually (e.g. via element), in order to verify any new bot sessions the script creates, or the sessions will show as unverified.
- You must have a management room ID on the target system, and configure it as management_room in the bot's config.ini.  
    Once the bot is running you must invite it into the management room. It should automatically accept the invitation.

## Installation

Create a folder for your project, and copy the contents of this repo into the folder

Run the following commands to install the necessary requirements:
```bash
python3 -m venv ./venv
. ./venv/bin/activate
pip install -e luxchatbot/
```

pip should automatically install all the requirements needed for the bot.

## Configuration

You can use the example code in example-bot/ to run your first bot.

Modify example-bot/config.ini with the correct information.

```ini
[homeserver]
homeserver = homeserver.luxchat4gov.lu
bot_uid = @mybot:homeserver.luxchat4gov.lu
access_token = youraccesstokenhere
device_id = yourdeviceIDhere

[config]
owner_id = @botowner:homeserver.luxchat4gov.lu
management_room = !yourroomid:homeserver.luxchat4gov.lu
bot_name = Example Bot
command_prefix = !
proxy = http://proxy.local:proxy_port
start_looper = True

[api]
api_enabled = True
api_host = 127.0.0.1
api_port = 5013
api_workers = 3
auth_required = True
api_password = #A random 20-chars password will be generated if left empty

[openweatherapi] #This section is specific to the example-bot, not necessary for your custom bot
api_key = my_api_key

```
Add your Access Token and Device ID to the configuration.
The example-bot config.ini contains an openweather api_key field, but it is not necessary for your own custom bots, you can remove it.

## Running the bot

### From source

To run your bot simply start the example-bot module:

python3 example-bot

If your bot account has not yet joined the configured management room, invite it into the room now. It should automatically join the room.

Now you can try sending your first command into the room:

```!help```

### With docker

To deploy your bot with docker, you can follow the instructions in [this documentation](./doc/docker.md).

## Files

The file structure of a bot should look like this :
```
.
├── luxchatbot
│   ├── autoverify.py
│   ├── __init__.py
│   ├── luxchatbot.py
│   ├── __main__.py
│   ├── README.md
│   ├── setup.py
│   ├── verify_with_emoji.py
│   └── watchdog.py
├── README.md
└── example-bot
    ├── modules/
    ├── bot.py
    ├── config.ini
    ├── __init__.py
    ├── __main__.py
    └── store/
```
Other folder (like the example-bot's models folder) can be added depending on your needs, but this is the default bot necessities.

## Custom bot creation

This part will describe each part you may want to edit when creating your own custom bot.

**All those parts aren't required**, if you see something that you're not interested in, just skip it.

For all these examples, we'll go use the example-bot as a base.

### Custom commands

To create a custom command, you can either create a new module, or add a command to a new one.


#### Module
To create a module, all you need to do is create a new python file in the modules/ folder and write those 4 lines.
```python
import niobot
import luxchatbot

class MyHelloModule(niobot.Module):    
```
You don't need to reference your module anywhere, all modules present in the modules/ folder will be mounter onto the bot at launch.

#### Creating a command
You can then create your custom command in your module using the @luxchatbot.command decorator
```python
@luxchatbot.command()
async def test_command(self, ctx: niobot.Context):
    pass
```

Command methods should always be async and contain at least two parameters : self, and ctx.
The ctx is the context of the command, it contains various information that you might find useful such as the room the message was sent from, or the user mxid, and more ([niobot.Context documentation](https://docs.nio-bot.dev/master/reference/context/)).

We now have a command that can be called (with <prefix>test_command) but does nothing.

#### Sending a message in a command

You could do many things in a command, but it is fairly common to give the user a message to let him know how the command went.

There are two ways to send messages to a room using a command :

Contextual response : 
```python
await self.bot.respond(ctx, "Hello, I'm a test command !")
```

Normal message :
```python
await self.bot.send_message(ctx.room.room_id, content="Hello, I'm a test command")
```

You will use contextual responses most of the time as they provide a way to visually see what message triggered the comamnd, useful in case multiple users are using commands in the same room.

However, as of now, there seems to be issues when deleting contextual responses, which is why we advise you to use normal messaging when you send a message you are planning on deleting afterwards (for sensitive data for example).

To delete a message, you can follow this example :
```python
response = await self.bot.send_message(ctx.room.room_id, "Hello, I'm a test command, and I'm self-destrucing in 10 seconds !")
await asyncio.sleep(10)
await self.bot.delete_message(ctx.room.room_id, response.event_id)
```

Congratulations, you can now call you favorite API and send the results to the user through a bot !

#### Command input parameters

We now have a bot that sends a message, but what if we want to give him more context ?

To achieve this goal, we add a parameter to our command funtion.
```python
@luxchatbot.command()
async def test_command(self, ctx: niobot.Context, val : str):
    if not self.bot.will_respond(ctx):
        return

    await self.bot.respond(ctx, f"Hello, I'm a test command ! You said : {val}")
```

So, if now if we call `!test_command test`, the bot will answer `Hello, I'm a test command ! You said : test`.
However, each parameter (because you could place the amount you want) is seperated by spaces (you can create multiple word arguments wrapping them in "" in the command call), which means that each parameter is only a single word.

Now, let's say we want to be able to return the whole sentence the user may have sent after the command call.
To achieve this gall, we only need to edit our command like this :
```python
@luxchatbot.command()
async def test_command(self, ctx: niobot.Context, *, val : str):
    if not self.bot.will_respond(ctx):
        return

    await self.bot.respond(ctx, f"Hello, I'm a test command ! You said : {val}")
```

This added * is a sign of a "greedy" arguments ([more about them in nio-bot documentation](https://docs.nio-bot.dev/master/reference/commands/#command-argument-detection)).

Now when we call the command with `!test_command This is a test`, the bot will answer `Hello, I'm a test command ! You said : This is a test` instead of returning an error.

Please note that you will always receive the data as either str or None, so you are advised to add type verifications and conversions when using int or other data types. You could technically just say your val is int type, and because python is the way it is, if you only receive numbers in your sting, it may work. But you can never be sure what the user passed is a real int or a string if you don't put verifications.

#### Management command

Sometimes, you might want to create a command that cannot be used by anyone but your administrators.
This is where management commands come into play.

A management command is a command that can only be answered inside of the management room configured in your [config.ini](#configuration).
This allows for a simple command access control.

In order for our command to turn into a management command, it it very simple :
```python
import niobot
import luxchatbot

class MyHelloModule(niobot.Module):  
    management = True

    @luxchatbot.command(management = management)
    async def test_command(self, ctx: niobot.Context, *, val : str):
        if not self.bot.will_respond(ctx, management = self.management):
            return

        await self.bot.respond(ctx, f"Hello, I'm a test command ! You said : {val}")
```

The self.bot.will_respond will verify that the room the command was called in is the management room, otherwise it won't return anything.

#### More about commands

If you didn't find what you wanted to know about commands, or if you just want to know more about them, please follow through the [additional command documentation](./doc/command.md).


### Custom endpoints

The API is one of the main ways to interact with the bots, allowing for other services from your infrastructure to call the endpoints to send reports or alerts to a room on the Luxchat servers.

In this section, we'll see how to create you own API endpoints and how to interact with the bot's API in general.

#### Simple send_message endpoint

To create your own endpoint, you'll have to go to your bot.py file and edit your custom LuxchatApi child class.

```python
class MyLuxchatApi(LuxchatApi):
    def add_custom_endpoints(self):

        @self.api.route('/send_message', methods=['POST'])
        def send_message():
            data = request.json
            result = self.send_to_bot(message=data['message'], room_id=data['room_id'])

            return jsonify({"message": result['message']}), result['code']
```

Here, we have created a simple endpoint that sends a message to a room.

All endpoints should be added in the add_custom_endpoints method.
We define our endpoint using the @LuxchatApi.api.route from our flask api, providing the handling function send_message().

When in the body of this handling function, we are in the context of a flask request, which means we can access the flask.request, allowing us to retrieve the json body sent by the user.

Here, we directly use the data from the body, but it is advised to add verifications to make sure your user provided the right information.
We then use the LuxchatApi.send_to_bot method to send a message to the bot in a specific room.
This will send our message to a multiprocessing queue that will process all the messages in its queue and send them to the server.

Once the message is processed and we received an answer, the queue will return a message and a code to tell the user wether the message could be successfully sent or not.

Example :
Call
```
curl -k -X POST --data '{"message" : "I'm a message", "room_id" : "!VcWvqxObBhcYWHyRGO:matrix.synapse.test"}' --header  'Content-Type: application/json' http://luxchatmessagebot:5015/send_message
```

The normal response would be `{"message":"Message sent successfully"}`.
However, if you tried the exact curl request we presented you and didn't touch the example-bot's config, you might have received this instead : `{"error":"Access denied"}`.
That is because of the [API authorization](#api-authorization).

#### API authorization

The API supports an Authorization to prevent that just anyone requests your bot's API.
This Authorization is configurable through the auth_required and api_password in the [config.ini](#configuration) of your bot.

By default, the app will generate a password to secure your API to a certain extent, preventing all request without the right password from going through.

This Authorization password should be placed in the Authorization header as is. Knowing this, we can correct our request from earlier :
```
curl -k -X POST --data '{"message" : "I'm a message", "room_id" : "!VcWvqxObBhcYWHyRGO:matrix.synapse.test"}' --header  'Content-Type: application/json' --header 'Authorization: ynoFA5yEE0z0Xsrs4J)z' http://luxchatmessagebot:5015/send_message
```

**Disclaimer** : This is not a __sufficient__ security for your bot's API, this is only the bare minimum, but we advise you to secure your API by making it unavailable for those outside your network.
If you are planning on using your own auhtorization method (like tokens for example), you are more than welcome to override the LuxchatApi.set_auth_verification() method in your custom API. 

### Custom looper

The looper is the simplest of all the ways to make your bot interact with the server. It simply executes a set of instructions at a set interval.

The custom looper goes into your custom LuxchatBot child class.
Here, we'll use the example-bot's looper as example.

```python

async def custom_looper(self):
    self.looper_sleep = 5
    room_id = self.config.get('config', 'management_room')
    start = self.tstamp['init_start']
    uptime = time.time() - start
    msg = f"Loop {self.custom_counter} - This Bot has been running for {uptime:.3f} seconds"
    self.custom_counter += 1
    await self.bot.send_message(room_id, content = msg)
```

As you can see, it is a simple looper that, every 5 seconds, sends the uptime of the bot and the number of loops it has made (the self.looper_sleep can also be put in the custom setup).

You can put anything here, an API call, a health check, etc.

### Overriding the default bot and api classes

When creating your custom bots, you may find yourself in need of overriding the default bot's api to set your own endpoints, or override the Bot class to change default behaviours (like not auto joining rooms for example).

This is done in your LuxchatBot class in the pre_setup method.

```python
def pre_setup(self):
    """
    This function is called before the startup of the bot, useful for defining the classes to use to initialize the API or the bot class.
    """

    #Override the niobitclass to our custom LuxchatNioBot class
    self.niobotclass = MyLuxchatNioBot

    #This overrides the default LuxchatApi with the custom one defined above
    self.apiclass = MyLuxchatApi
```

This pre_setup runs just before the initialization of the bot and the API while the custom_setup runs just after, allowing us to load our commands on the bot for example.

### Custom configuration

When building your own bots, you may want to add new configuration fields for api keys, conenction info to a database, or activating/deactivating services.

For optional config parameters, you can manage them in the LuxchatBot.validate_config() method.
```python
def validate_config(self):
    super().validate_config()
    
    if not "api_key" in self.config["openweatherapi"]:
        self.config["openweatherapi"]["api_key"] = "default_api_key"
```

However, sometimes you want, on top of validation, to make sure your config field is not empty.
For this purpose, you can override the LuxchatBot.get_required_config_values() method.

```python
 def get_required_config_values(self):
        required_values = super().get_required_config_values()

        required_values["openweatherapi"] = {
            "api_key" : None,
        }

        return required_values
```
This successfully adds the openweatherapi section and the api_key field to the required config values, throwing an error if they are left empty at the bot launch.

### Logging

To adapt logging to your needs, you can add a logging.ini file to your bot folder. You can find an example of what it could look like in the example-bot/logging.ini.sample.

This file will configure your logging to adapt logging formats, handlers (if you want to log into a file intead of the console), and many other logging parameters like the log_level.

To use the default logger, you can simply call the "log" attribute on your custom LuxchatBot child class like you can see below.
```python
class MyLuxchatBot(LuxchatBot):
    def custom_setup(self):
        self.log.info("From the default logger")
```

You can also call log from your commands like so:
```python
import niobot
import luxchatbot

class MyHelloModule(niobot.Module):

    @luxchatbot.command()
    async def hello(self, ctx: niobot.Context, *, val : str):
        """Log hello"""
        self.bot.lx_bot.log.info("Hello !")
```

#### Custom logger

If you want a custom logger, simply add its name to the list of logger keys and then add a section like the following logger_myCustomLogger to specify its level, handlers, qualname, and propagation.
```ini

[loggers]
keys=root, luxchatbot, myCustomLogger

[logger_myCustomLogger]
level=INFO
handlers=consoleHandler
qualname=myCustomLogger
propagate=0
```

Then, in your code, you can create your logger inside your LuxchatBot child class like so :
```python
class MyLuxchatBot(LuxchatBot):
    def custom_setup(self):

        #Set your custom logger
        self.logger = logging.getLogger("myCustomLogger")
        self.logger.info("Custom logger working")
```

If you want to know more about how to configure your loggers, you can read [the official documentation](https://docs.python.org/3/library/logging.config.html)


#### Why set propagate to 0

In the sample logging config, there are two elements that might surprise some.
- First, our root logging level is error, which really doesn't log a lot
- Second, our default logger is set to propagate 0

These choices are driven by the enormous amount of logs that nio-bot logs in info and warning levels.
That is why we choose to set the minimum logging level to ERROR.
Our logger propagation is set to 0 because it allows it to log in whatever level we set regardless of the root logger level.