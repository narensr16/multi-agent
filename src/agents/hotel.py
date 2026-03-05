"""
hotel.py — Hotel Agent

Searches Tavily for hotels at the destination within budget.
Returns up to 5 clean, properly-named hotel property names.
"""

import os
import re
import json
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_groq import ChatGroq

load_dotenv()

_TAVILY_KEY = os.getenv("TAVILY_API_KEY", "").strip()
_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

# ── Cleanup ───────────────────────────────────────────────────────────────────
_SITE_SUFFIX_RE = re.compile(
    r"\s*[|\-–—,]\s*(tripadvisor|booking\.com|makemytrip|agoda|expedia"
    r"|hotels\.com|goibibo|oyorooms|airbnb|yatra|cleartrip|in\.com).*$",
    re.IGNORECASE,
)

# ── Noise: reject these patterns — they are article/page headings ─────────────
_NOISE_RE = re.compile(
    r"\b(best|top|cheap|budget|luxury|list|guide|review|book|compare"
    r"|hotels in|resorts in|places to|things to|itinerary|package|price"
    r"|deals|discount|offers|near|around|collection|selection"
    r"|look no further|boasts|known for|perfect for|features|located)\b",
    re.IGNORECASE,
)

# ── Require recognised brand/type keyword in the name ─────────────────────────
_BRAND_RE = re.compile(
    r"\b(hotel|resort|inn|suites?|palace|villa|lodge|retreat|homestay"
    r"|hyatt|marriott|taj|oberoi|radisson|hilton|novotel|lemon tree"
    r"|holiday inn|ibis|vivanta|leela|itc|trident|aloft|courtyard"
    r"|planet hollywood|caravela|kenilworth|cidade de goa|alila|riva"
    r"|four seasons|w hotel|westin|sheraton|st\.?\s*regis|intercontinental"
    r"|crowne plaza|doubletree|renaissance|park hyatt|andaz)\b",
    re.IGNORECASE,
)

# ── Extraction regex: hotel name ending on a keyword ──────────────────────────
# Must start with a capital letter and end with a known hotel brand/type word
_EXTRACT_RE = re.compile(
    r"(?<!\w)([A-Z][A-Za-z&'\-\s]{1,40}"
    r"(?:Hotel|Resort|Inn|Suites?|Palace|Villa|Lodge|Retreat|Homestay|Residency|Hostel"
    r"|Hyatt|Marriott|Taj|Oberoi|Radisson|Hilton|Novotel|Lemon Tree"
    r"|Holiday Inn|Ibis|Vivanta|Leela|Trident|Aloft|Westin|Sheraton"
    r"|Planet Hollywood|Caravela|Cidade de Goa|Kenilworth|St Regis"
    r"|Four Seasons|Courtyard|Crowne Plaza|Doubletree|Renaissance"
    r"|Park Hyatt|Andaz)(?:\s+[A-Z][A-Za-z&,\-]{0,20}){0,3})"
)


def _clean(title: str) -> str:
    title = re.sub(r"\s+", " ", title)
    title = _SITE_SUFFIX_RE.sub("", title).strip().strip(",.:").strip()
    
    # Strip long descriptive prefixes that are often captured before "The X Hotel"
    # Example: "German Rhineland inspired The Fullerton Hotel" -> "The Fullerton Hotel"
    if " The " in title:
        title = "The " + title.split(" The ", 1)[1]
    
    # Remove standalone adjectives at the start
    title = re.sub(r"^(?:Historic|Famous|Popular|Beautiful|Luxurious|Luxury|Cheap|Budget|Best|Top)\s+", "", title, flags=re.IGNORECASE)
    
    return title.strip()


def _is_valid(name: str) -> bool:
    if not name or not (5 <= len(name) <= 45):
        return False
    # Must NOT be a web-page heading
    if _NOISE_RE.search(name):
        return False
    # Sentence fragments (comma + lowercase) usually mean bad extraction
    if re.search(r",\s+[a-z]", name):
        return False
    return True


def _extract(text: str) -> list:
    results = []
    # Try the strict regex first (needs a brand keyword at the end)
    for m in _EXTRACT_RE.finditer(text or ""):
        name = _clean(m.group(1))
        if _is_valid(name) and name not in results:
            results.append(name)
            
    # If we didn't get enough, try a looser fallback that just looks for Title Case sequences
    # ending in any typical hotel-like suffix.
    if len(results) < 5:
        loose_re = re.compile(r"(?<!\w)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s+(?:Hotel|Resort|Inn|Suites?|Palace|Villa|Lodge|Retreat|Homestay))")
        for m in loose_re.finditer(text or ""):
            name = _clean(m.group(1))
            if _is_valid(name) and name not in results:
                results.append(name)
                
    return results


def hotel_agent(state: dict) -> dict:
    destination = state.get("destination", "")
    budget      = int(state.get("budget", 50000))

    if not destination or destination == "Unknown":
        return {"hotels": ["Hotel search skipped: destination unknown."]}
    if not _TAVILY_KEY:
        return {"hotels": ["Hotel search skipped: TAVILY_API_KEY not configured."]}

    nightly = budget // 5
    tier = (
        "budget affordable" if nightly < 2000
        else "mid-range" if nightly < 5000
        else "luxury 5-star"
    )

    hotels: list = []

    try:
        client = TavilyClient(api_key=_TAVILY_KEY)

        # Pass 1 — structured advanced search
        q1 = f"top {tier} hotel names to stay in {destination} India list"
        res1 = client.search(q1, max_results=8, search_depth="advanced")
        
        chunks = [res1.get("answer") or ""] + [r.get("content") or "" for r in res1.get("results", [])]
        combined_text = " ".join(chunks)

        if _GROQ_KEY and _GROQ_KEY != "your_groq_api_key_here":
            try:
                llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
                prompt = (
                    f"Extract up to 5 real, popular hotels in {destination} from the text below.\n"
                    f"Return ONLY a raw JSON list of strings containing exactly the clean hotel names.\n"
                    f'Do not include conversational text, adjectives, or descriptions (e.g. "The Fullerton Hotel", not "German Rhineland inspired The Fullerton Hotel").\n'
                    f"If no hotels are found, return [].\n\nText: {combined_text}"
                )
                res = llm.invoke(prompt)
                content = res.content.strip()
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                parsed = json.loads(content.strip())
                if isinstance(parsed, list):
                    hotels = [str(h).strip() for h in parsed if len(str(h)) > 3]
            except Exception as e:
                print(f"Groq parsing failed: {e}")

        # Fallback to Regex if LLM didn't get enough
        if len(hotels) < 3:
            for chunk in chunks:
                for name in _extract(chunk):
                    if name not in hotels:
                        hotels.append(name)
                if len(hotels) >= 8:
                    break

        # Pass 2 — fallback with a broader query
        if len(hotels) < 5:
            q2 = f"famous hotel resorts in {destination} India names"
            res2 = client.search(q2, max_results=6)
            for chunk in [r.get("content") or "" for r in res2.get("results", [])]:
                for name in _extract(chunk):
                    if name not in hotels:
                        hotels.append(name)
                if len(hotels) >= 8:
                    break

    except Exception as e:
        return {"hotels": [f"Hotel search failed: {e}"]}

    hotels = hotels[:5]
    if not hotels:
        hotels = ["No hotel names found — try searching booking.com or makemytrip.com"]

    return {"hotels": hotels}
