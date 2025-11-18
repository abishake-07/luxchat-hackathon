# Command additional documentation

This documentation is a more in-depth documentation about what is possible with luxchatbot commands.

If you didn't read it already, it is greaty advised to read the [introduction to the commands in the main documentation](../README.md#custom-commands).

Some of these modifications are only little miscelaneous facts or ways to edit your commands like you want to. You probably don't need to read every one of these to answer to you use case, only read what you're looking for


#### Changing a command's name

Changing a command's name is simple, you only need to change a parameter in the @luxchatbot.command decorator.

```python
@luxchatbot.command(name="testcommand")
async def hello(self, ctx: niobot.Context, *, val : str):
    """Say hello"""

    #It is advised to sanitize inputs depending on your use case
    
    if self.bot.will_respond(ctx):
        await self.bot.respond(ctx, f"Hello, you said : {val}")
```

As you can see, we set the name of the command in the decorator, and we can now call it using !testcommand instead of defaulting to the handler method name (!hello).

#### Creating a custom command decorator (execute code for each command)

Sometimes, there are actions you want to execute with all your bot's command, like verifying if a management command is called from a management room, verifying a user's mxid is in your user access database, or sanitizing all the input passed to your commands.
To solve this kind of issue, you can create a custom command decorator.

First, we'll need to import a few additional libraries to be able to create our decorator and wrap it. You can add these imports at the top of your bot.py script.
```python
import typing
from collections.abc import Callable
from command import LuxchatCommand
from functools import wraps
```

Then, at the bottom of your bot.py script, outside a class, you can create a custom decorator by following this example :
```python
def examplebotCommand(name: typing.Optional[str] = None, management = False, reply_all = False) -> Callable:
    def decorator(func):
        @wraps(func)
        async def wrapper(command_module, context : niobot.Context, **kwargs):

            #Verify management room for managment commands
            if not command_module.bot.will_respond(context, management = management):
                return

            #Sanitize all the arguments before passing them to the commands
            sanitized_kwargs = {}

            for key, value in kwargs.items():
                sanitized_kwargs[key] = sanitize_user_input(value)

            return await func(command_module, context, **sanitized_kwargs)

        nonlocal name
        name = name or func.__name__
        description = func.__doc__

        cmd = LuxchatCommand(name, wrapper, description = description, is_management = management)

        wrapper.__nio_command__ = cmd

        return wrapper
    return decorator
```

In this example, we sanitize all the parameters provided to the bot and we verify that the bot can respond (if it's a management comamnd, we verify that command was called from the management room).

All the operations in this wrapper will be executed for all the commands defined with the @examplebotCommand decorator.
There isn't a lot of changes in our commands, we just replace the @luxchatbot.comamnd by @examplebotCommand :
```python
@examplebotCommand()
async def hello(self, ctx: niobot.Context, *, val : str):
    """Say hello"""

    #It is advised to sanitize inputs depending on your use case
    
    if self.bot.will_respond(ctx):
        await self.bot.respond(ctx, f"Hello, you said : {val}")
```

For this, we need a new import in our modules :
```python
from bot import examplebotCommand
```

You can now create your own custom command decorator to reduce code redundancy, improve your commands readability, and reduce copy/paste errors.