"""
map.py — Map Agent

Generates a clickable Google Maps URL for all attractions in the itinerary.
Works 100% free with no API key — uses public maps.google.com URL format.
"""

import re
import urllib.parse


def _extract_places(itinerary: str) -> list:
    """Pull attraction names from formatted itinerary text."""
    places = []
    # Match lines like: "  Morning: Eravikulam National Park (₹200)"
    for line in itinerary.split("\n"):
        match = re.search(r"^\s*(?:Morning|Afternoon|Evening):\s*(.+?)(?:\s*\(|$)", line, re.IGNORECASE)
        if match:
            place = match.group(1).strip()
            if place.lower() not in {"relax", "rest", "tbd", "unknown"} and len(place) > 3:
                places.append(place)
    return list(dict.fromkeys(places))


def map_agent(state: dict) -> dict:
    """
    Build a Google Maps URL from itinerary attractions.
    Writes: map_url (str)
    """
    destination = state.get("destination", "")
    itinerary   = state.get("itinerary", "")

    if not destination or destination == "Unknown" or not itinerary:
        return {"map_url": ""}

    places = _extract_places(itinerary)

    if not places:
        # Fallback: just open a search for the destination
        q = urllib.parse.quote(f"tourist attractions in {destination}")
        return {"map_url": f"https://maps.google.com/maps?q={q}"}

    if len(places) == 1:
        q = urllib.parse.quote(f"{places[0]}, {destination}")
        return {"map_url": f"https://maps.google.com/maps?q={q}"}

    # Multiple places — use search/dir format with waypoints
    # The most universally compatible free approach: link to a search for the first place
    # and show all as a bulleted legend in the display
    first = urllib.parse.quote(f"{places[0]}, {destination}")
    base_url = f"https://maps.google.com/maps?q={first}"

    return {
        "map_url":    base_url,
        "map_places": places,      # for use in the final display
    }
