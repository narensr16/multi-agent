"""
flight.py — Amadeus Flight Search Agent

Uses the Amadeus Self-Service API (test environment) to find real flights
to the destination city. Returns the top 3 cheapest one-way options.

API docs: https://developers.amadeus.com/self-service/category/flights
"""

import os
from dotenv import load_dotenv

load_dotenv()

AMADEUS_KEY    = os.getenv("AMADEUS_API_KEY",    "").strip()
AMADEUS_SECRET = os.getenv("AMADEUS_API_SECRET", "").strip()

# ── City → IATA airport code lookup (covers major Indian cities) ──────────────
CITY_TO_IATA = {
    "goa":        "GOI",
    "mumbai":     "BOM",
    "delhi":      "DEL",
    "bangalore":  "BLR",
    "hyderabad":  "HYD",
    "chennai":    "MAA",
    "kolkata":    "CCU",
    "pune":       "PNQ",
    "ahmedabad":  "AMD",
    "jaipur":     "JAI",
    "kochi":      "COK",
    "manali":     "KUU",   # Kullu-Manali airport
    "shimla":     "SLV",
    "varanasi":   "VNS",
    "agra":       "AGR",
    "lucknow":    "LKO",
    "patna":      "PAT",
    "bhubaneswar":"BBI",
    "ranchi":     "IXR",
    "srinagar":   "SXR",
    "leh":        "IXL",
    "amritsar":   "ATQ",
    "coimbatore": "CJB",
    "visakhapatnam": "VTZ",
    "nagpur":     "NAG",
    "indore":     "IDR",
    "udaipur":    "UDR",
    "guwahati":   "GAU",
    "port blair": "IXZ",
    "andaman":    "IXZ",
    "darjeeling": "IXB",
    "kerala":     "COK",
    "ooty":       "CJB",
}

# Nearest airport when destination is not directly served
NEAREST_HUB = {
    "kodaikanal": "MAA",  # Chennai
    "coorg":      "BLR",  # Bangalore
    "mysore":     "BLR",
    "rishikesh":  "DEL",
    "rajasthan":  "JAI",
}

AIRLINE_NAMES = {
    "AI": "Air India",  "6E": "IndiGo",    "SG": "SpiceJet",
    "UK": "Vistara",    "QP": "Akasa Air", "G8": "Go First",
    "IX": "Air Asia",   "9W": "Jet Airways","S5": "Star Air",
}


def _get_iata(destination: str) -> str | None:
    d = destination.lower().strip()
    code = CITY_TO_IATA.get(d) or NEAREST_HUB.get(d)
    return code


def _format_duration(iso: str) -> str:
    """Convert 'PT1H30M' → '1h 30m'."""
    import re
    h = re.search(r"(\d+)H", iso)
    m = re.search(r"(\d+)M", iso)
    parts = []
    if h:
        parts.append(f"{h.group(1)}h")
    if m:
        parts.append(f"{m.group(1)}m")
    return " ".join(parts) or iso


def flight_agent(state: dict) -> dict:
    """
    Search for the 3 cheapest one-way flights to state["destination"].
    Departure assumed to be a major hub closest to the user (defaults to DEL).
    Writes: flights (formatted string)
    """
    destination = state.get("destination", "")
    budget      = float(state.get("budget", 50000))

    if not destination or destination == "Unknown":
        return {"flights": "Flight search skipped: destination unknown."}

    if not AMADEUS_KEY or not AMADEUS_SECRET:
        return {"flights": "Flight search skipped: AMADEUS_API_KEY / AMADEUS_API_SECRET not configured."}

    origin_name = state.get("origin", "")
    dest_iata = _get_iata(destination)
    if not dest_iata:
        return {"flights": f"Flight search skipped: no IATA code found for '{destination}'."}

    origin_iata = _get_iata(origin_name) if origin_name else None
    if not origin_iata or origin_iata == dest_iata:
        # Fallback to DEL, or BOM if destination is DEL
        origin_iata = "BOM" if dest_iata == "DEL" else "DEL"

    try:
        from amadeus import Client, ResponseError
        amadeus = Client(
            client_id=AMADEUS_KEY,
            client_secret=AMADEUS_SECRET,
        )

        # Use a near-future date for test env (30 days ahead)
        from datetime import date, timedelta
        depart_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin_iata,
            destinationLocationCode=dest_iata,
            departureDate=depart_date,
            adults=1,
            max=5,
            currencyCode="INR",
        )

        offers = response.data
        if not offers:
            return {"flights": f"No flights found from {origin_iata} to {dest_iata}."}

        # Sort by price and take top 3
        offers.sort(key=lambda o: float(o["price"]["grandTotal"]))
        top3 = offers[:3]

        lines = [f"  (Results shown for {origin_iata} → {dest_iata}, {depart_date})\n"]
        for i, offer in enumerate(top3, 1):
            seg      = offer["itineraries"][0]["segments"][0]
            carrier  = seg["carrierCode"]
            airline  = AIRLINE_NAMES.get(carrier, carrier)
            departs  = seg["departure"]["at"][11:16]           # HH:MM
            arrives  = seg["arrival"]["at"][11:16]
            duration = _format_duration(offer["itineraries"][0]["duration"])
            price    = float(offer["price"]["grandTotal"])
            tag      = " ✅ Within budget" if price <= budget * 0.10 else ""

            lines.append(
                f"  {i}. {airline} ({carrier})  |  {departs} → {arrives}"
                f"  |  Duration: {duration}  |  💰 ₹{price:,.0f}{tag}"
            )

        return {"flights": "\n".join(lines)}

    except Exception as e:
        return {"flights": f"  Flight search failed: {e}"}
