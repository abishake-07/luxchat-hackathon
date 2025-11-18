class MeteoEntry:

    def __init__(self, main : str, description : str, country : str, temp_f : float, icon_id : str):
        self.main = main
        self.description = description
        self.country = country
        self.temp = self.kelvin_to_celsius(temp_f)
        self.icon_url = f"https://openweathermap.org/img/wn/{icon_id}@2x.png"


    def kelvin_to_celsius(self, temp_kelvin : float) -> float:
        return round(temp_kelvin - 273.15, 2)
