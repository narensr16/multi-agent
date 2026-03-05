"""Budget tools - calculates estimated total travel cost."""
from typing import List, Dict


def calculate_budget(
    destination: str,
    days: int,
    num_people: int,
    hotels: List[Dict],
    transport_options: List[Dict],
) -> Dict:
    """
    Calculate a breakdown of estimated travel costs.

    Returns a dict with cost components and total.
    """
    # Pick cheapest available hotel
    if hotels:
        cheapest_hotel = min(hotels, key=lambda h: h["price_per_night"])
        accommodation_cost = cheapest_hotel["price_per_night"] * days * num_people
        hotel_name = cheapest_hotel["name"]
    else:
        accommodation_cost = 1500 * days * num_people
        hotel_name = "Standard accommodation"

    # Pick cheapest transport
    if transport_options:
        cheapest_transport = min(transport_options, key=lambda t: t["cost"])
        transport_cost = cheapest_transport["cost"] * num_people * 2  # round trip
        transport_mode = cheapest_transport["mode"]
    else:
        transport_cost = 1000 * num_people * 2
        transport_mode = "Standard transport"

    # Food estimate: ₹500/person/day for budget travel
    food_cost = 500 * days * num_people

    # Sightseeing & misc: ₹300/person/day
    misc_cost = 300 * days * num_people

    total = accommodation_cost + transport_cost + food_cost + misc_cost

    return {
        "total": total,
        "breakdown": {
            "accommodation": accommodation_cost,
            "hotel_used": hotel_name,
            "transport": transport_cost,
            "transport_mode": transport_mode,
            "food": food_cost,
            "sightseeing_misc": misc_cost,
        },
        "days": days,
        "people": num_people,
    }


def format_budget(budget_result: Dict) -> str:
    """Format the budget breakdown into a readable string."""
    b = budget_result["breakdown"]
    total = budget_result["total"]
    lines = [
        f"  • Accommodation ({budget_result['days']} nights @ {b['hotel_used']}): ₹{b['accommodation']:,}",
        f"  • Transport ({b['transport_mode']}, round trip):            ₹{b['transport']:,}",
        f"  • Food & Dining:                                           ₹{b['food']:,}",
        f"  • Sightseeing & Miscellaneous:                             ₹{b['sightseeing_misc']:,}",
        f"  ──────────────────────────────────────────────────────",
        f"  TOTAL ESTIMATED COST:                                      ₹{total:,}",
    ]
    return "\n".join(lines)
