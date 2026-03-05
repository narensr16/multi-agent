"""Hotel tools - returns mock hotel listings with estimated prices."""
from typing import List, Dict


def get_hotels(destination: str, budget: float) -> List[Dict]:
    """Return a list of hotels at the destination based on budget."""
    hotel_data = {
        "kodaikanal": [
            {"name": "Lake View Stay", "price_per_night": 1500, "rating": 4.2, "type": "Budget"},
            {"name": "Hilltop Resort", "price_per_night": 3500, "rating": 4.6, "type": "Mid-range"},
            {"name": "Sterling Kodaikanal", "price_per_night": 6000, "rating": 4.8, "type": "Luxury"},
            {"name": "Cloud End Villa", "price_per_night": 2500, "rating": 4.4, "type": "Mid-range"},
        ],
        "goa": [
            {"name": "Beach Shack Inn", "price_per_night": 1800, "rating": 4.0, "type": "Budget"},
            {"name": "Sunset Paradise", "price_per_night": 4000, "rating": 4.5, "type": "Mid-range"},
            {"name": "Grand Hyatt Goa", "price_per_night": 9000, "rating": 4.9, "type": "Luxury"},
        ],
        "manali": [
            {"name": "Snow Valley Hostel", "price_per_night": 800, "rating": 4.1, "type": "Budget"},
            {"name": "Apple Country Resort", "price_per_night": 3000, "rating": 4.5, "type": "Mid-range"},
            {"name": "Span Resort & Spa", "price_per_night": 7500, "rating": 4.8, "type": "Luxury"},
        ],
        "shimla": [
            {"name": "Ridge View Lodge", "price_per_night": 1200, "rating": 4.0, "type": "Budget"},
            {"name": "Wildflower Hall", "price_per_night": 5000, "rating": 4.7, "type": "Mid-range"},
            {"name": "Oberoi Cecil", "price_per_night": 10000, "rating": 4.9, "type": "Luxury"},
        ],
    }

    key = destination.lower().strip()
    hotels = []
    for city, city_hotels in hotel_data.items():
        if city in key or key in city:
            hotels = city_hotels
            break

    if not hotels:
        # Generic hotels for unknown destinations
        hotels = [
            {"name": f"{destination} Budget Inn", "price_per_night": 1000, "rating": 3.8, "type": "Budget"},
            {"name": f"{destination} Comforts Hotel", "price_per_night": 2500, "rating": 4.2, "type": "Mid-range"},
            {"name": f"{destination} Grand Hotel", "price_per_night": 5000, "rating": 4.6, "type": "Luxury"},
        ]

    # Filter by budget: average nightly cost should not exceed 30% of total budget
    max_price = budget * 0.3 if budget > 0 else float("inf")
    affordable = [h for h in hotels if h["price_per_night"] <= max_price]
    return affordable if affordable else hotels[:2]


def format_hotels(hotels: List[Dict]) -> str:
    """Format the hotel list into a readable string."""
    if not hotels:
        return "No hotels found."
    lines = []
    for h in hotels:
        lines.append(f"  • {h['name']} ({h['type']}) - ₹{h['price_per_night']:,}/night | ⭐ {h['rating']}")
    return "\n".join(lines)
