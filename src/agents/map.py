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
    # Match lines like: "Morning  : Visit Marina Bay Sands" or "Visit Gardens by the Bay"
    for m in re.finditer(r"Visit\s+(.+?)(?:\s*\(|$)", itinerary, re.MULTILINE):
        place = m.group(1).strip().strip(".,")
        # Skip generic filler lines
        skip = {"local area", "local markets", "a café", "local dinner", "surroundings", "explore local"}
        if place.lower() not in skip and len(place) > 4:
            places.append(place)
    return list(dict.fromkeys(places))  # deduplicate while preserving order


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
