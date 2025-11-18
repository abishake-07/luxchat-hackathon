import niobot
import luxchatbot
from models.meteoProvider import MeteoProvider
from models.meteoEntry import MeteoEntry

class MyMeteoModule(niobot.Module):
        management = True
        
        @luxchatbot.command(management = management)
        async def meteo(self, ctx: niobot.Context, city_name : str):
            """Gets current meteo in a city provided by the user"""
            if not self.bot.will_respond(ctx, management = self.management):
                return
            
            #It is advised to sanitize inputs depending on your use case

            meteoProvider = MeteoProvider(api_key=self.bot.lx_bot.config["openweatherapi"]["api_key"])

            meteoEntry : MeteoEntry = meteoProvider.get_meteo_by_city_name(city_name.lower())

            response = f"Current meteo in {city_name} is {meteoEntry.description} and temperature is around {meteoEntry.temp}°C"

            await self.bot.send_message(ctx.room.room_id, content=response)

