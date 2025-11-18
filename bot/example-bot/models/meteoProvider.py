import requests
from models.meteoEntry import MeteoEntry

class MeteoProvider:

    def __init__(self, api_key):
        self.__api_key = api_key

    def get_meteo_by_lat_lon(self, lat : float, lon : float):
        data = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.__api_key}",
            timeout=15
        )

        return self.format_meteo_data(data.json())
    
    def get_meteo_by_city_name(self, city_name: str):
        data = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={self.__api_key}",
            timeout=15
        )

        return self.format_meteo_data(data.json())

    def format_meteo_data(self, data : dict) -> MeteoEntry:
        return MeteoEntry(
            main = data["weather"][0]["main"],
            description = data["weather"][0]["description"],
            country = data["sys"]["country"],
            temp_f = data["main"]["temp"],
            icon_id = data["weather"][0]["icon"]
        )