"""Transport tools - returns available transport options for a destination."""
from typing import List, Dict


def get_transport_options(destination: str) -> List[Dict]:
    """Return available transport methods and estimated costs to the destination."""
    transport_data = {
        "kodaikanal": [
            {"mode": "Bus", "duration": "8-10 hours from Chennai", "cost": 500, "comfort": "Economy"},
            {"mode": "Train + Taxi", "duration": "Train to Kodai Road, then 1.5hr taxi", "cost": 900, "comfort": "Moderate"},
            {"mode": "Flight + Taxi", "duration": "Fly to Madurai, then 3hr drive", "cost": 4000, "comfort": "Comfortable"},
        ],
        "goa": [
            {"mode": "Train", "duration": "8-12 hours from Mumbai", "cost": 800, "comfort": "Moderate"},
            {"mode": "Flight", "duration": "1-2 hours from major cities", "cost": 3500, "comfort": "Comfortable"},
            {"mode": "Bus", "duration": "12-14 hours from Mumbai", "cost": 600, "comfort": "Economy"},
        ],
        "manali": [
            {"mode": "Bus", "duration": "10-12 hours from Delhi", "cost": 700, "comfort": "Economy"},
            {"mode": "Flight + Taxi", "duration": "Fly to Bhuntar, then 1hr drive", "cost": 5000, "comfort": "Comfortable"},
            {"mode": "Private Car", "duration": "12-14 hours from Delhi", "cost": 3000, "comfort": "Moderate"},
        ],
        "shimla": [
            {"mode": "Bus", "duration": "5-6 hours from Delhi", "cost": 400, "comfort": "Economy"},
            {"mode": "Train (Toy Train)", "duration": "Kalka to Shimla: 5.5 hours (scenic)", "cost": 300, "comfort": "Moderate"},
            {"mode": "Flight + Taxi", "duration": "Fly to Chandigarh, then 2hr drive", "cost": 3500, "comfort": "Comfortable"},
        ],
    }

    key = destination.lower().strip()
    for city, options in transport_data.items():
        if city in key or key in city:
            return options

    # Generic options for unknown destinations
    return [
        {"mode": "Bus", "duration": "Varies by distance", "cost": 600, "comfort": "Economy"},
        {"mode": "Train", "duration": "Varies by distance", "cost": 900, "comfort": "Moderate"},
        {"mode": "Flight", "duration": "Quickest option", "cost": 4000, "comfort": "Comfortable"},
    ]


def format_transport(options: List[Dict]) -> str:
    """Format transport options into a readable string."""
    if not options:
        return "No transport options found."
    lines = []
    for t in options:
        lines.append(f"  • {t['mode']} - {t['duration']} | ₹{t['cost']:,} per person ({t['comfort']})")
    return "\n".join(lines)
