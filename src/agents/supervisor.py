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
    "kodaikanal", "goa", "manali", "shimla", "kerala", "ooty",
    "rajasthan", "delhi", "mumbai", "kolkata", "jaipur", "agra",
    "varanasi", "rishikesh", "darjeeling", "coorg", "mysore",
    "hyderabad", "bangalore", "chennai", "pune", "ahmedabad",
    "leh", "ladakh", "spiti", "munnar", "alleppey", "andaman",
    "gokarna", "hampi", "udaipur", "jodhpur", "kochi",
]


def _extract_destination(text: str) -> str:
    """Extract destination from the query text."""
    text_lower = text.lower()

    # First, try known destinations (most reliable)
    for dest in KNOWN_DESTINATIONS:
        if dest in text_lower:
            return dest.title()

    # Fallback: regex for "trip to X", "visit X", "go to X" etc.
    match = re.search(
        r"(?:visit|go to|travel to|trip to|plan.*?to|heading to|in)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)"
        r"(?:\s+for|\s+with|\s*$)",
        text,
        re.IGNORECASE,
    )
    if match:
        candidate = match.group(1).strip()
        # Avoid matching common words like "a", "the" etc.
        if len(candidate) > 2 and candidate.lower() not in ("the", "for", "with"):
            return candidate.title()

    return "Unknown"


def _extract_days(text: str) -> int:
    """
    Supports formats:
      5 day / 5 days / 5-day trip / 7 day trip
    """
    match = re.search(r"(\d+)\s*[-]?\s*day", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
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

    # Very naive regex extractions for demonstration.
    # In a full LangGraph pattern, you might use an LLM here to extract structured args.
    dest_match = re.search(r"(?:to|visit) ([A-Za-z\s]+)(?: for| with)?", query, re.IGNORECASE)
    days_match = re.search(r"(\d+)\s*-?\s*day", query, re.IGNORECASE)
    
    # Try to find an origin (e.g. "from Mumbai", "from Bangalore")
    origin_match = re.search(r"from\s+([A-Za-z\s]+)(?:\s+to|\s+visit|\s+for|\s+with|$)", query, re.IGNORECASE)

    # Looking for a budget amount with optional currency/commas
    budget_match = re.search(r"(?:budget(?: of)?|rs\.?|₹)\s*([\d,]+)", query, re.IGNORECASE)
    if not budget_match:
        budget_match = re.search(r"(\d{4,})", query) # standalone large number

    destination = dest_match.group(1).strip() if dest_match else "Unknown"
    days_str = days_match.group(1) if days_match else "3"
    origin = origin_match.group(1).strip() if origin_match else "DEL"

    try:
        budget_str = budget_match.group(1).replace(",", "") if budget_match else "50000"
        budget = float(budget_str)
    except Exception:
        budget = 50000.0

    msg = f"Extracted Goal -> Dest: {destination}, Origin: {origin}, Days: {days_str}, Budget: {budget}"
    return {
        "destination": destination,
        "origin": origin,
        "days": days_str,
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

    SEP  = "=" * 56
    SEP2 = "-" * 56

    # ── Hotels block (aligned bullet list) ──────────────────────────────────
    if isinstance(hotels_raw, list) and hotels_raw:
        hotel_lines = "\n".join(f"  • {h}" for h in hotels_raw[:5])
    elif isinstance(hotels_raw, str):
        hotel_lines = hotels_raw
    else:
        hotel_lines = "  • No hotel data available."

    # ── Cost block ────────────────────────────────────────────────────────────
    if isinstance(cost_info, dict):
        hotel_cost       = cost_info.get("hotel_cost", 0)
        transport_cost   = cost_info.get("transport_cost", 0)
        transport_label  = cost_info.get("transport_label", "Transport")
        food_cost        = cost_info.get("food_cost", 0)
        misc_cost        = cost_info.get("misc_cost", 0)
        total            = cost_info.get("total", 0)
        verdict          = "Within budget ✅" if total <= budget else "Exceeds budget ⚠️"

        cost_block = (
            f"  {'Accommodation':<18}: ₹{hotel_cost:>8,.0f}\n"
            f"  {transport_label:<18}: ₹{transport_cost:>8,.0f}\n"
            f"  {'Food':<18}: ₹{food_cost:>8,.0f}\n"
            f"  {'Misc':<18}: ₹{misc_cost:>8,.0f}\n"
            f"  {'-' * 32}\n"
            f"  {'TOTAL':<18}: ₹{total:>8,.0f}\n"
            f"  {verdict}"
        )
    else:
        cost_block = "  Cost data unavailable."

    summary = (
        f"\n{SEP}\n"
        f"🌍  AI TRAVEL PLAN\n"
        f"{'=' * 17}\n\n"
        f"  Destination    : {destination}\n"
        f"  Duration       : {days} day(s)\n"
        f"  Budget         : ₹{int(budget):,}\n\n"
        f"{SEP2}\n"
        f"  🌤  WEATHER\n"
        f"{SEP2}\n"
        f"  {weather_raw}\n\n"
        f"{SEP2}\n"
        f"  🏨  HOTELS\n"
        f"{SEP2}\n"
        f"{hotel_lines}\n\n"
        f"{SEP2}\n"
        f"  🚗  TRANSPORT OPTIONS\n"
        f"{SEP2}\n"
        f"{transport_raw}\n\n"
        f"{SEP2}\n"
        f"  ✈  FLIGHTS (Live via Amadeus)\n"
        f"{SEP2}\n"
        f"{flights_raw}\n\n"
        f"{SEP2}\n"
        f"  🗓  DAY-BY-DAY ITINERARY\n"
        f"{SEP2}\n"
        f"{itinerary_raw}\n\n"
        f"{SEP2}\n"
        f"  💰  ESTIMATED COST\n"
        f"{SEP2}\n"
        f"{cost_block}\n"
        f"{SEP}\n"
    )

    return {
        "final_response": summary,
        "messages": [AIMessage(content=summary)],
    }
