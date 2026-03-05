"""
budget.py — Budget Agent

Calculates a realistic trip cost estimate.

Formula:
    hotel_cost     = days * 3000
    food_cost      = days * 700
    misc_cost      = days * 500
    transport_cost = cheapest Amadeus flight price (if found) else 1500
    total          = sum of above

Writes: estimated_cost (dict with itemised breakdown + total)
"""

import re


def _parse_cheapest_flight(flights_text: str) -> float | None:
    """
    Parse the cheapest flight price from the flights string produced by flight_agent.
    Looks for patterns like '₹9,608' or '₹4,820' in the first result line.
    Returns the float value, or None if no price found.
    """
    if not flights_text or "skipped" in flights_text.lower() or "failed" in flights_text.lower():
        return None

    # Find all ₹ prices
    prices = re.findall(r"₹([\d,]+)", flights_text)
    if not prices:
        return None

    amounts = []
    for p in prices:
        try:
            amounts.append(float(p.replace(",", "")))
        except ValueError:
            continue

    return min(amounts) if amounts else None


def budget_agent(state: dict) -> dict:
    """
    Estimate trip cost for state["days"], using real flight price if available.
    Writes: estimated_cost (dict)
    """
    days   = state.get("days", 3)
    budget = state.get("budget", 0)

    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 3

    # Try to pull cheapest flight from Amadeus results
    flights_text    = state.get("flights") or ""
    flight_price    = _parse_cheapest_flight(flights_text)
    transport_cost  = flight_price if flight_price else 1500
    transport_label = "Flight (Amadeus)" if flight_price else "Local Transport"

    hotel_cost = days * 3000
    food_cost  = days * 700
    misc_cost  = days * 500
    total      = hotel_cost + transport_cost + food_cost + misc_cost

    return {
        "estimated_cost": {
            "hotel_cost":      hotel_cost,
            "transport_cost":  transport_cost,
            "transport_label": transport_label,
            "food_cost":       food_cost,
            "misc_cost":       misc_cost,
            "total":           total,
        }
    }