"""
budget.py — Budget Agent (Currency-Aware)

Detects the destination's local currency, estimates realistic costs in that
currency, then converts everything to INR for display.

Currency conversion rates (approximate, Mar 2026):
  EUR → INR : 90    (Europe)
  USD → INR : 84    (USA, Canada, SE Asia, South Asia)
  GBP → INR : 107   (UK)
  AED → INR : 23    (Middle East)
  AUD → INR : 55    (Australia/NZ)
  JPY → INR : 0.56  (Japan)
  KRW → INR : 0.062 (South Korea)
  SGD → INR : 63    (Singapore)
  THB → INR : 2.5   (Thailand)
  MYR → INR : 19    (Malaysia)
  IDR → INR : 0.0053(Indonesia)

Writes: estimated_cost (dict with itemised breakdown + total in INR)
"""
import requests
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()
_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

def detect_country_and_currency(destination: str) -> tuple[str, str, str]:
    dest_lower = destination.lower()
    if "goa" in dest_lower or "india" in dest_lower or "bangalore" in dest_lower:
        return "India", "INR", "₹"
    if "singapore" in dest_lower:
        return "Singapore", "SGD", "$"
    if "paris" in dest_lower or "france" in dest_lower:
        return "France", "EUR", "€"
    if "tokyo" in dest_lower or "japan" in dest_lower:
        return "Japan", "JPY", "¥"
    if "bangkok" in dest_lower or "thailand" in dest_lower:
        return "Thailand", "THB", "฿"

    if _GROQ_KEY and _GROQ_KEY != "your_groq_api_key_here":
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
            prompt = f"What is the country, 3-letter ISO currency code, and currency symbol for the travel destination '{destination}'? Return only a raw JSON: {{\"country\": \"...\", \"code\": \"...\", \"symbol\": \"...\"}} without quotes or markdown."
            res = llm.invoke(prompt)
            content = res.content.strip()
            if content.startswith("```json"): content = content[7:-3]
            elif content.startswith("```"): content = content[3:-3]
            parsed = json.loads(content.strip())
            return parsed.get("country", "India"), parsed.get("code", "INR").upper(), parsed.get("symbol", "₹")
        except Exception:
            pass
    return "India", "INR", "₹"

def get_exchange_rate_to_inr(currency_code: str) -> float:
    code = currency_code.upper()
    if code == "INR": return 1.0
        
    try:
        url = "https://open.er-api.com/v6/latest/INR"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            rate = data.get("rates", {}).get(code)
            if rate: return 1.0 / float(rate)
    except Exception:
        pass
        
    fallbacks = {
        "USD": 84.0, "EUR": 90.0, "GBP": 107.0, "SGD": 62.0, "JPY": 0.56,
        "AED": 23.0, "THB": 2.5, "MYR": 19.0, "AUD": 55.0, "IDR": 0.0053
    }
    return fallbacks.get(code, 84.0)

# ── Currency configs per region ────────────────────────────────────────────────
# Each entry:
#   currency    : ISO code shown to user
#   symbol      : display prefix
#   inr_rate    : 1 unit of local currency = X INR
#   hotel_night : realistic nightly hotel cost (local currency)
#   food_day    : realistic food spend per day (local currency)
#   misc_day    : sightseeing / transport per day (local currency)
#   flight_est  : round-trip / one-way flight estimate (local currency)

_REGION_CONFIG = {
    "india": dict(
        currency="INR", symbol="₹", inr_rate=1,
        hotel_night=2500, food_day=600, misc_day=400, flight_est=4500,
    ),
    "south_asia": dict(
        currency="USD", symbol="$", inr_rate=84,
        hotel_night=40,  food_day=20,  misc_day=12,  flight_est=200,
    ),
    "southeast_asia_budget": dict(  # Thailand, Vietnam, Indonesia, Cambodia
        currency="USD", symbol="$", inr_rate=84,
        hotel_night=35,  food_day=18,  misc_day=15,  flight_est=250,
    ),
    "southeast_asia_premium": dict(  # Singapore, KL
        currency="USD", symbol="$", inr_rate=84,
        hotel_night=80,  food_day=35,  misc_day=25,  flight_est=350,
    ),
    "middle_east": dict(
        currency="AED", symbol="AED", inr_rate=23,
        hotel_night=250, food_day=100, misc_day=70,  flight_est=1800,
    ),
    "europe": dict(
        currency="EUR", symbol="€", inr_rate=90,
        hotel_night=120, food_day=55,  misc_day=35,  flight_est=750,
    ),
    "uk": dict(
        currency="GBP", symbol="£", inr_rate=107,
        hotel_night=110, food_day=45,  misc_day=30,  flight_est=650,
    ),
    "usa_canada": dict(
        currency="USD", symbol="$", inr_rate=84,
        hotel_night=130, food_day=60,  misc_day=40,  flight_est=1100,
    ),
    "japan": dict(
        currency="JPY", symbol="¥", inr_rate=0.56,
        hotel_night=10000, food_day=4000, misc_day=3000, flight_est=60000,
    ),
    "south_korea": dict(
        currency="KRW", symbol="₩", inr_rate=0.062,
        hotel_night=80000, food_day=35000, misc_day=20000, flight_est=500000,
    ),
    "australia_nz": dict(
        currency="AUD", symbol="AUD", inr_rate=55,
        hotel_night=130, food_day=55,  misc_day=35,  flight_est=1500,
    ),
    "africa": dict(
        currency="USD", symbol="$", inr_rate=84,
        hotel_night=80,  food_day=35,  misc_day=25,  flight_est=900,
    ),
}

# ── Destination → region mapping ───────────────────────────────────────────────
_EUROPE = {
    "barcelona", "madrid", "paris", "rome", "milan", "venice", "florence",
    "amsterdam", "berlin", "munich", "frankfurt", "zurich", "geneva",
    "vienna", "prague", "budapest", "brussels", "lisbon", "athens",
    "stockholm", "copenhagen", "oslo", "helsinki", "warsaw", "krakow",
    "porto", "seville", "valencia", "naples", "bologna", "marseille",
    "lyon", "nice", "bordeaux", "zurich", "berne", "salzburg",
    "dubrovnik", "split", "zagreb", "sarajevo", "sofia", "bucharest",
    "riga", "tallinn", "vilnius", "reykjavik", "iceland",
    "spain", "france", "germany", "italy", "netherlands", "portugal",
    "austria", "switzerland", "greece", "belgium", "denmark", "sweden",
    "norway", "finland", "poland", "czech", "hungary", "croatia",
    "europe", "schengen",
}
_UK = {"london", "edinburgh", "manchester", "glasgow", "birmingham", "uk", "england", "scotland", "ireland", "dublin"}
_USA_CANADA = {"new york", "los angeles", "chicago", "san francisco", "miami", "las vegas", "seattle", "Toronto", "vancouver", "montreal", "cancun", "mexico city", "usa", "canada", "america"}
_JAPAN = {"tokyo", "osaka", "kyoto", "hiroshima", "nara", "fukuoka", "hokkaido", "japan"}
_SOUTH_KOREA = {"seoul", "busan", "jeju", "korea", "south korea"}
_AUS_NZ = {"sydney", "melbourne", "brisbane", "perth", "cairns", "gold coast", "auckland", "wellington", "christchurch", "australia", "new zealand"}
_MIDDLE_EAST = {"dubai", "abu dhabi", "doha", "riyadh", "jeddah", "muscat", "kuwait", "bahrain", "sharjah", "qatar", "oman", "saudi"}
_SE_ASIA_PREMIUM = {"singapore", "kuala lumpur", "kl", "penang"}
_SE_ASIA_BUDGET = {"bangkok", "phuket", "chiang mai", "bali", "denpasar", "jakarta", "lombok", "ho chi minh", "hanoi", "da nang", "saigon", "phnom penh", "yangon", "manila", "cebu", "pattaya", "krabi", "vietnam", "thailand", "indonesia", "cambodia", "myanmar", "philippines", "malaysia"}
_SOUTH_ASIA = {"colombo", "kathmandu", "pokhara", "dhaka", "maldives", "male", "thimphu", "paro", "bhutan", "nepal", "sri lanka", "bangladesh"}
_AFRICA = {"nairobi", "cape town", "johannesburg", "cairo", "casablanca", "addis ababa", "kenya", "south africa", "egypt", "morocco", "ethiopia"}


def _detect_region(destination: str) -> str:
    d = destination.lower().strip()
    if d in _EUROPE or any(e in d for e in _EUROPE):         return "europe"
    if d in _UK or any(e in d for e in _UK):                return "uk"
    if d in _USA_CANADA or any(e in d for e in _USA_CANADA): return "usa_canada"
    if d in _JAPAN or any(e in d for e in _JAPAN):          return "japan"
    if d in _SOUTH_KOREA or any(e in d for e in _SOUTH_KOREA): return "south_korea"
    if d in _AUS_NZ or any(e in d for e in _AUS_NZ):        return "australia_nz"
    if d in _MIDDLE_EAST or any(e in d for e in _MIDDLE_EAST): return "middle_east"
    if d in _SE_ASIA_PREMIUM or any(e in d for e in _SE_ASIA_PREMIUM): return "southeast_asia_premium"
    if d in _SE_ASIA_BUDGET or any(e in d for e in _SE_ASIA_BUDGET): return "southeast_asia_budget"
    if d in _SOUTH_ASIA or any(e in d for e in _SOUTH_ASIA): return "south_asia"
    if d in _AFRICA or any(e in d for e in _AFRICA):        return "africa"
    return "india"


_REGION_LABELS = {
    "india":                   "🇮🇳 India (Domestic)",
    "south_asia":              "🌏 South Asia (USD)",
    "southeast_asia_budget":   "🌏 SE Asia Budget (USD)",
    "southeast_asia_premium":  "🌏 SE Asia Premium (USD)",
    "middle_east":             "🌍 Middle East (AED)",
    "europe":                  "🌍 Europe (EUR)",
    "uk":                      "🌍 UK (GBP)",
    "usa_canada":              "🌎 USA/Canada (USD)",
    "japan":                   "🌏 Japan (JPY)",
    "south_korea":             "🌏 South Korea (KRW)",
    "australia_nz":            "🌏 Australia/NZ (AUD)",
    "africa":                  "🌍 Africa (USD)",
}


def _parse_cheapest_flight_inr(flights_text: str) -> float | None:
    """Parse cheapest flight price from Amadeus output (already in INR)."""
    if not flights_text:
        return None
    lower = flights_text.lower()
    if any(kw in lower for kw in ("skipped", "failed", "budget too low", "no flights", "no iata")):
        return None
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
    Estimate trip cost in local currency, convert to INR.
    Writes: estimated_cost (dict)
    """
    days        = state.get("days", 3)
    budget_inr  = float(state.get("budget", 10000))
    destination = str(state.get("destination", "") or "")

    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 3
    if days < 1:
        days = 1

    # ── Detect region ─────────────────────────────────────────────────────────
    region  = _detect_region(destination)
    cfg     = _REGION_CONFIG[region]
    rate    = cfg["inr_rate"]           # 1 local unit = rate INR
    sym     = cfg["symbol"]
    cur     = cfg["currency"]
    
    if region == "india":
        sym = "₹"
        cur = "INR"

    # ── Hotel: Use Dynamic Tavily String (hotel_price_raw)  ──
    hotel_raw = state.get("hotel_price_raw") or "INR 5000"
    nums = re.findall(r"[\d,]+(?:\.\d+)?", hotel_raw)
    
    if nums:
        scraped_night_local = float(nums[0].replace(",", ""))
        # Currency detect in raw string
        raw_cur_match = re.search(r"[A-Z]{3}|[₹$€£]", hotel_raw)
        raw_cur = raw_cur_match.group(0) if raw_cur_match else cur
        if raw_cur == "$": raw_cur = "USD"
        elif raw_cur == "₹": raw_cur = "INR"
        
        # Get rate for the scraped currency
        scraped_rate = _REGION_CONFIG.get("india" if raw_cur == "INR" else "usa_canada", {}).get("inr_rate", 84.0)
        if raw_cur == "SGD": scraped_rate = 63.0
        elif raw_cur == "EUR": scraped_rate = 93.0
        elif raw_cur == "GBP": scraped_rate = 107.0
        
        # Safety cap: If per-night > 200,000 INR, it's likely a total stay price misparsed
        hotel_inr_night = scraped_night_local * scraped_rate
        if hotel_inr_night > 200000:
            hotel_inr_night = 5000.0 # fallback
            hotel_local_night = hotel_inr_night / (rate or 1.0)
        else:
            hotel_local_night = scraped_night_local if raw_cur == cur else (hotel_inr_night / (rate or 1.0))

        hotel_inr = hotel_inr_night * days
        hotel_display_per_night = f"{raw_cur} {scraped_night_local:,.2f}"
    else:
        hotel_inr = cfg["hotel_night"] * rate * days
        hotel_display_per_night = f"{cur} {cfg['hotel_night']}"

    # ── Food & Misc ──────────────────────────────────────────────────────────
    food_inr = cfg["food_day"] * rate * days
    
    itinerary_cost = state.get("activities_cost") or 0.0
    misc_inr = float(itinerary_cost) if itinerary_cost else (cfg["misc_day"] * rate * days)

    # ── Transport (flight) ───────────────────────────────────────────────────
    flight_inr = _parse_cheapest_flight_inr(state.get("flights") or "")
    if not flight_inr or flight_inr < 1000:
        flight_inr = cfg["flight_est"] * rate

    # ── Final Assembly ───────────────────────────────────────────────────────
    total_inr = round(hotel_inr + flight_inr + food_inr + misc_inr, 2)
    budget_status = "Within budget ✅" if total_inr <= budget_inr else "Exceeds budget ⚠️"

    # Match exact label format: (₹77,616.00 ($924.00 (3 days × SGD308.0)))
    h_local_detail = f"₹{hotel_inr:,.2f}  (${hotel_inr/84.0:,.2f} ({days} days × {hotel_display_per_night}))"

    return {
        "estimated_cost": {
            "region":             _REGION_LABELS.get(region, region),
            "inr_rate":           f"1 {cur} ≈ ₹{rate}",
            "hotel_local":        h_local_detail,
            "transport_cost":     flight_inr,
            "food_cost":          food_inr,
            "misc_cost":          misc_inr,
            "total":              total_inr,
            "budget_status":      budget_status,
        }
    }