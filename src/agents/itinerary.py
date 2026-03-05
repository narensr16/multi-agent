"""
itinerary.py — Day-by-Day Itinerary Agent

Uses Tavily to find top attractions at the destination, then builds a
clean day-by-day plan (exactly 3 slots per day: Morning / Afternoon / Evening).
Filters out web noise from results.
"""

import os
import re
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

_TAVILY_KEY = os.getenv("TAVILY_API_KEY", "").strip()

# ── Blocklist: single/partial words that are NOT attraction names ──────────────
_BLOCKLIST = {
    "today", "daily", "budget", "flights", "rooms", "during", "see", "visit",
    "things", "activities", "places", "tours", "tips", "guide", "area",
    "information", "overview", "highlights", "options", "available",
    "practical", "travel", "tourism", "tourist", "booking", "deals",
    "explore", "experience", "india", "international", "national",
    "package", "price", "cost", "free", "new", "best", "top", "most",
    "famous", "popular", "beautiful", "amazing", "great", "good",
    "world", "heritage", "culture", "local", "traditional", "nearby",
    "morning", "evening", "afternoon", "night", "day", "time",
}

# Words that suggest a real place/attraction
_PLACE_INDICATORS = re.compile(
    r"\b(beach|fort|temple|church|museum|market|lake|falls|island"
    r"|garden|palace|park|sanctuary|basilica|bridge|square|bay|hill"
    r"|village|waterfall|cave|wildlife|reserve|point|lighthouse"
    r"|chapel|cathedral|monastery|ruins|valley|peak|plateau"
    r"|bagh|mahal|mandir|dargah|jung)\b",
    re.IGNORECASE,
)

# Extraction: proper noun phrase (2-5 title-case words)
_PLACE_RE = re.compile(
    r"(?<!\w)([A-Z][A-Za-z']+(?:\s+(?:of\s+)?[A-Z][A-Za-z']+){1,4})(?=\s|,|\.|\))"
)


def _clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[\s*]+", " ", text)
    return text.strip()


def _extract_attractions(combined: str, destination: str, max_items: int = 18) -> list:
    dest_lower = destination.lower()
    seen = set()
    results = []

    for m in _PLACE_RE.finditer(combined):
        raw = m.group(1).strip()
        
        # Strip trailing loose words often caught by Title Case regex
        # e.g., "Rama Fort One", "Tiracol Fort Image", "Visit ... Now"
        raw = re.sub(r"\s+(One|Of|The|A|An|Image|Picture|Photo|Guide|Tour|Best|Top|Now|There|Here|Visit|View|Why|You|Should)\b.*$", "", raw, flags=re.IGNORECASE)
        raw = raw.strip()

        words = raw.split()
        word_count = len(words)

        # Must be 2–5 words
        if not (2 <= word_count <= 5):
            continue

        # All individual words must NOT be in blocklist
        if any(w.lower() in _BLOCKLIST for w in words):
            continue

        # Skip if it's just the destination name or "South/North X"
        if raw.lower() == dest_lower or raw.lower() in [f"south {dest_lower}", f"north {dest_lower}"]:
            continue

        # Must either contain a place-type word OR start with a recognisable prefix
        has_indicator = (
            _PLACE_INDICATORS.search(raw)
            or re.search(r"\b(Old|Fort|North|South|East|West|Upper|Lower|New|Grand)\b", raw)
        )
        if not has_indicator and word_count < 3:
            continue

        key = raw.lower()
        if key not in seen:
            seen.add(key)
            results.append(raw)

        if len(results) >= max_items:
            break

    return results


# Curated fallback attractions per well-known destination
_FALLBACK = {
    "goa": [
        "Baga Beach", "Calangute Beach", "Anjuna Beach", "Palolem Beach",
        "Old Goa Churches", "Fort Aguada", "Dudhsagar Falls",
        "Panaji Latin Quarter", "Anjuna Flea Market", "Chapora Fort",
    ],
    "manali": [
        "Rohtang Pass", "Solang Valley", "Hadimba Temple", "Manu Temple",
        "Old Manali Village", "Beas River", "Naggar Castle",
        "Kullu Valley", "Rahala Falls", "Jogini Waterfall",
    ],
    "kerala": [
        "Alleppey Backwaters", "Munnar Tea Gardens", "Periyar Wildlife Sanctuary",
        "Kovalam Beach", "Fort Kochi Heritage", "Athirapally Waterfalls",
        "Varkala Cliff Beach", "Thekkady Spice Plantation",
    ],
    "shimla": [
        "Mall Road", "Ridge Ground", "Jakhu Temple", "Kufri Hill Station",
        "Christ Church", "Chadwick Falls", "Green Valley",
        "Viceregal Lodge", "Annandale Ground",
    ],
}


def _build_itinerary(attractions: list, days: int, destination: str) -> str:
    slots = ["🌅 Morning   ", "☀️  Afternoon", "🌙 Evening   "]
    lines = []
    idx = 0
    n = len(attractions)

    for d in range(1, days + 1):
        lines.append(f"\n  📅 Day {d}")
        lines.append(f"  {'─' * 40}")

        if d == 1:
            lines.append(f"     {slots[0]}: Arrive in {destination}, check-in & freshen up")
            # 2 activities for day 1
            day_items = attractions[idx: idx + 2]
            idx += 2
            for i, place in enumerate(day_items):
                lines.append(f"     {slots[i + 1]}: Visit {place}")
            if len(day_items) < 2:
                lines.append(f"     {slots[2]}: Relax and explore local area")

        elif d == days:
            # 2 activities for last day
            day_items = attractions[idx: idx + 2] if idx < n else []
            idx += 2
            for i, place in enumerate(day_items):
                lines.append(f"     {slots[i]}: Visit {place}")
            if len(day_items) < 2:
                lines.append(f"     {slots[1]}: Rest and explore surroundings")
            lines.append(f"     {slots[2]}: Pack up and depart from {destination}")

        else:
            # 3 activities for middle days
            day_items = attractions[idx: idx + 3] if idx < n else []
            idx += 3
            for i, place in enumerate(day_items):
                lines.append(f"     {slots[i]}: Visit {place}")
            # Pad missing slots
            for i in range(len(day_items), 3):
                filler = ["Explore local markets", "Relax at a café", "Local dinner & leisure"][i % 3]
                lines.append(f"     {slots[i]}: {filler}")

    return "\n".join(lines)


def itinerary_agent(state: dict) -> dict:
    destination = state.get("destination", "")
    days        = int(state.get("days", 3))

    if not destination or destination == "Unknown":
        return {"itinerary": "Itinerary skipped: destination unknown."}

    attractions = []

    if _TAVILY_KEY:
        try:
            client = TavilyClient(api_key=_TAVILY_KEY)
            query  = (
                f"top tourist attractions places to visit in {destination} India "
                f"beaches forts temples nature sightseeing must see"
            )
            result = client.search(query, max_results=6, search_depth="advanced")

            parts = [_clean(result.get("answer") or "")]
            parts += [_clean(r.get("content") or "") for r in result.get("results") or []]
            combined = " ".join(p for p in parts if p)

            attractions = _extract_attractions(combined, destination)

        except Exception:
            pass

    # Use curated fallback if extraction failed or yielded too little
    if len(attractions) < days * 2:
        fb = _FALLBACK.get(destination.lower(), [])
        for item in fb:
            if item not in attractions:
                attractions.append(item)

    itinerary = _build_itinerary(attractions, days, destination)
    return {"itinerary": itinerary}
