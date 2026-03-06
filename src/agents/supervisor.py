"""
supervisor.py — Supervisor Agent

Responsibilities:
  supervisor_init  → parse user_query, extract destination / days / budget
  supervisor_final → assemble final_response from all agent outputs
"""

import sys
import os
import re
from langchain_core.messages import AIMessage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from state import AgentState


KNOWN_DESTINATIONS = [
    "kerala", "kodaikanal", "goa", "manali", "shimla", "ooty",
    "rajasthan", "delhi", "mumbai", "kolkata", "jaipur", "agra",
    "varanasi", "rishikesh", "darjeeling", "coorg", "mysore",
    "hyderabad", "bangalore", "chennai", "pune", "ahmedabad",
    "leh", "ladakh", "spiti", "munnar", "alleppey", "andaman",
    "gokarna", "hampi", "udaipur", "jodhpur", "kochi", "karnataka",
    "tamil nadu", "maharashtra", "kashmir", "srinagar",
]


def _extract_destination(text: str) -> str:
    # Look for common patterns
    # We use a non-greedy match with a lookahead to stop before keywords like from, for, with, budget
    patterns = [
        r'(?:visit|travel to|trip to|plan.*?to|heading|go to|into|in)\s+([a-zA-Z\s]+?)(?=\s+(?:from|for|with|budget)|$)',
        r'to\s+([a-zA-Z\s]+?)(?=\s+(?:from|for|with|budget)|$)'
    ]
    
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            dest = match.group(1).strip()
            # Clean up nested prefixes if any (e.g. "visit visit Kanyakumari")
            for _ in range(3): # up to 3 times to be safe
                for prefix in ["visit ", "go to ", "to ", "into ", "in "]:
                    if dest.lower().startswith(prefix):
                        dest = dest[len(prefix):].strip()
            
            if dest.lower() not in ('go a', 'have a', 'take a', 'trip', 'the'):
                return dest.title()

    # Fallback to known destinations
    text_lower = text.lower()
    for dest in KNOWN_DESTINATIONS:
        if re.search(r'\b' + re.escape(dest) + r'\b', text_lower):
            if not re.search(r'from\s+' + re.escape(dest), text_lower):
                return dest.title()
    
    return "Unknown"


def _extract_origin(text: str) -> str:
    m = re.search(r'from\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)(?:\s+to|\s+for|\s+with|\s+budget|\s*$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().title()
    return "DEL"


def _extract_days(text: str) -> int:
    """
    Supports formats:
      5 day / 5 days / 5-day trip / 5-trip / 5 nights / 1 week
    """
    # Match "5-day", "5 days", "5 day"
    match = re.search(r"(\d+)\s*[-]?\s*day", text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Match "5-trip", "5 night", "5 nights"
    match = re.search(r"(\d+)\s*[-]?\s*(?:trip|night|nights)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Match "1 week" / "2 weeks"
    match = re.search(r"(\d+)\s*[-]?\s*week", text, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 7

    return 3


def _extract_budget(text: str) -> float:
    """
    Supports formats:
      50000 / ₹50000 / budget of 50000 / 50k / rs 50000
    """
    # Explicit budget phrases first
    match = re.search(
        r"(?:budget\s+of\s+|budget\s*[:=]?\s*|₹|rs\.?\s*)(\d[\d,]*k?)",
        text,
        re.IGNORECASE,
    )
    if match:
        raw = match.group(1).replace(",", "").lower()
        if raw.endswith("k"):
            return float(raw[:-1]) * 1000
        return float(raw)

    # Generic large standalone number (budget is typically 4–6 digits)
    numbers = re.findall(r"\b(\d{4,6})\b", text)
    if numbers:
        return float(numbers[-1])

    return 10000.0


def supervisor_init(state: AgentState) -> dict:
    """
    Parse the user query to extract the desired destination, duration in days,
    origin city (if specified), and budget. Default origin is DEL.
    Writes: destination, days, budget, origin, messages
    """
    query = state.get("user_query", "")

    destination = _extract_destination(query)
    days = _extract_days(query)
    budget = _extract_budget(query)
    origin = _extract_origin(query)

    msg = f"Extracted Goal -> Dest: {destination}, Origin: {origin}, Days: {days}, Budget: {budget}"
    return {
        "destination": destination,
        "origin": origin,
        "days": str(days),
        "budget": budget,
        "messages": [AIMessage(content=msg)]
    }


def supervisor_final(state: AgentState) -> dict:
    """
    Assemble the final travel plan from all agent outputs.
    Writes: final_response, messages
    """
    destination = state.get("destination", "N/A")
    days        = state.get("days", 0)
    budget      = state.get("budget", 0)

    weather_raw   = state.get("weather") or "Weather data unavailable."
    hotels_raw    = state.get("hotels") or []
    transport_raw = state.get("transport") or "Transport data unavailable."
    flights_raw   = state.get("flights") or "Flight data unavailable."
    itinerary_raw = state.get("itinerary") or "Itinerary data unavailable."
    cost_info     = state.get("estimated_cost")
    map_url       = state.get("map_url", "")
    map_places    = state.get("map_places", [])

    SEP  = "=" * 56
    SEP2 = "-" * 56

    # ── Hotels block (aligned bullet list) ──────────────────────────────────
    if isinstance(hotels_raw, list) and hotels_raw:
        hotel_lines = "\n".join(f"  • {h}" for h in hotels_raw[:5])
    elif isinstance(hotels_raw, str):
        hotel_lines = hotels_raw
    else:
        hotel_lines = "  • No hotel data available."

    # ── Transport block (multi-line bullet support) ──────────────────────────
    if transport_raw:
        transport_fmt = "\n".join(f"  • {line.strip()}" for line in transport_raw.split("\n") if line.strip())
    else:
        transport_fmt = "  • Transport data unavailable."

    # ── Map block ─────────────────────────────────────────────────────────────
    if map_url:
        map_block = f"  🔗 View on Google Maps: {map_url}\n"
        if map_places:
            map_block += "  📍 Attractions:\n"
            for place in map_places[:8]:
                q = place.replace(" ", "+")
                link = f"https://maps.google.com/maps?q={q}"
                map_block += f"      ∙ {place} → {link}\n"
    else:
        map_block = "  Map unavailable.\n"

    # ── Cost block ─────────────────────────────────────────────────────────────
    if isinstance(cost_info, dict):
        hotel_cost      = cost_info.get("hotel_cost", 0)
        transport_cost  = cost_info.get("transport_cost", 0)
        transport_label = cost_info.get("transport_label", "Transport")
        food_cost       = cost_info.get("food_cost", 0)
        misc_cost       = cost_info.get("misc_cost", 0)
        total           = cost_info.get("total", 0)
        region_label    = cost_info.get("region", "")
        currency        = cost_info.get("currency", "INR")
        inr_rate        = cost_info.get("inr_rate", 1)
        # Local currency sub-labels (only shown for non-INR)
        hotel_local     = cost_info.get("hotel_local", "")
        food_local      = cost_info.get("food_local", "")
        misc_local      = cost_info.get("misc_local", "")
        transport_local = cost_info.get("transport_local", "")
        verdict         = "Within budget ✅" if total <= budget else "Exceeds budget ⚠️"

        def _local(s): return f"  ({s})" if s else ""

        region_note = f"  Cost Region      : {region_label}\n" if region_label else ""
        rate_note   = f"  Exchange Rate    : 1 {currency} ≈ ₹{inr_rate:.1f}\n" if currency != "INR" else ""
        cost_block = (
            f"{region_note}"
            f"{rate_note}"
            f"  {'Accommodation':<18}: ₹{hotel_cost:>8,.2f}{_local(hotel_local)}\n"
            f"  {transport_label:<18}: ₹{transport_cost:>8,.2f}{_local(transport_local)}\n"
            f"  {'Food':<18}: ₹{food_cost:>8,.2f}{_local(food_local)}\n"
            f"  {'Misc / Activities':<18}: ₹{misc_cost:>8,.2f}{_local(misc_local)}\n"
            f"  {'-' * 42}\n"
            f"  {'TOTAL':<18}: ₹{total:>8,.2f}\n"
            f"  {verdict}"
        )
    else:
        cost_block = "  Cost data unavailable."


    dest_clean = destination.replace("Visit ", "").replace("to ", "").strip()

    # ── Final Report Assembly ────────────────────────────────────────────────
    summary = (
        f"{SEP}\n"
        f"🌍  AI TRAVEL PLAN\n"
        f"{'=' * 17}\n\n"
        f"  Destination    : {dest_clean}\n"
        f"  Duration       : {days} day(s)\n"
        f"  Budget         : ₹{int(budget):,}\n\n"
        f"{SEP2}\n"
        f"  🌤  WEATHER\n"
        f"{SEP2}\n"
        f"  {weather_raw}\n\n"
        f"{SEP2}\n"
        f"  🏨  HOTELS\n"
        f"{SEP2}\n"
        f"  {hotel_lines}\n\n"
        f"{SEP2}\n"
        f"  🚗  TRANSPORT OPTIONS\n"
        f"{SEP2}\n"
        f"  {transport_fmt}\n\n"
        f"{SEP2}\n"
        f"  ✈  FLIGHTS (Live via Amadeus)\n"
        f"{SEP2}\n"
        f"  {flights_raw.replace('\n', '\n  ')}\n\n"
        f"{SEP2}\n"
        f"  🗓  DAY-BY-DAY ITINERARY\n"
        f"{SEP2}\n"
        f"  {itinerary_raw.replace('\n', '\n  ')}\n\n"
        f"{SEP2}\n"
        f"  🗺  MAP\n"
        f"{SEP2}\n"
        f"  {map_block}\n"
        f"  💰  ESTIMATED COST\n"
        f"{SEP2}\n"
    )

    if isinstance(cost_info, dict):
        # Match exact labels and format
        reg_label = cost_info.get("region", "Domestic")
        rate_info = cost_info.get("inr_rate", "N/A")
        h_cost = cost_info.get("hotel_local", "N/A")
        f_inr = cost_info.get("transport_cost", 0)
        food_inr = cost_info.get("food_cost", 0)
        misc_inr = cost_info.get("misc_cost", 0)
        total_inr = cost_info.get("total", 0)
        status = cost_info.get("budget_status", "Exceeds budget ⚠️")

        summary += (
            f"  Cost Region      : {reg_label}\n"
            f"  Exchange Rate    : {rate_info}\n"
            f"  Accommodation     : {h_cost}\n"
            f"  Flight (Amadeus)  : ₹{f_inr:,.2f}  (₹{f_inr:,.0f})\n"
            f"  Food              : ₹{food_inr:,.2f}  (INR)\n"
            f"  Misc / Activities : ₹{misc_inr:,.2f}  (INR)\n"
            f"  {'-' * 42}\n"
            f"  TOTAL             : ₹{total_inr:,.2f}\n"
            f"  {status}\n"
        )
    else:
        summary += "  Cost data unavailable.\n"

    summary += f"{SEP}\n"

    return {
        "final_response": summary,
        "messages": [AIMessage(content=summary)],
    }
