"""Weather tools - returns mock weather data for a given destination."""


def get_weather(destination: str) -> str:
    """Return mock weather information for the given destination."""
    weather_data = {
        "kodaikanal": "Cool and foggy, temperatures between 8°C - 20°C. Best to carry woollens.",
        "goa": "Warm and sunny, temperatures between 25°C - 35°C. Expect occasional sea breeze.",
        "manali": "Cold and snowy, temperatures between -5°C - 10°C. Heavy woolens required.",
        "kerala": "Tropical and humid, temperatures between 22°C - 32°C. Possible rain showers.",
        "rajasthan": "Hot and arid, temperatures between 30°C - 45°C. Carry sunscreen and light cotton.",
        "shimla": "Cool and pleasant, temperatures between 5°C - 18°C. Mild woolens recommended.",
        "ooty": "Cool and misty, temperatures between 10°C - 22°C. Light woolens advised.",
        "delhi": "Moderate climate, temperatures between 15°C - 30°C depending on season.",
        "mumbai": "Humid and warm, temperatures between 24°C - 35°C. High humidity.",
        "kolkata": "Hot and humid, temperatures between 25°C - 38°C.",
    }
    key = destination.lower().strip()
    for city, weather in weather_data.items():
        if city in key or key in city:
            return weather
    return f"Pleasant weather expected at {destination} with moderate temperatures. Carry light clothing and a jacket."
