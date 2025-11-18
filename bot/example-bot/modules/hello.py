import niobot
import luxchatbot

class MyHelloModule(niobot.Module):

    @luxchatbot.command()
    async def hello(self, ctx: niobot.Context, *, val : str):
        """Say hello"""

        #It is advised to sanitize inputs depending on your use case
        
        if self.bot.will_respond(ctx):
            await self.bot.respond(ctx, f"Hello, you said : {val}")
