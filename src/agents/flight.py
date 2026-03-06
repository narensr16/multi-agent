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

# ── City → IATA airport code lookup ──────────────────────────────────────────
# Covers airports with direct service. Also accepts abbreviations & alternate names.
CITY_TO_IATA = {
    # ── Metro & Major Cities ─────────────────────────────────────────────────
    "goa":              "GOI",  "panaji":          "GOI",
    "north goa":        "GOI",  "south goa":       "GOI",
    "mumbai":           "BOM",  "bombay":          "BOM",
    "delhi":            "DEL",  "new delhi":       "DEL",
    "bangalore":        "BLR",  "bengaluru":       "BLR",  "blr": "BLR",
    "hyderabad":        "HYD",  "hyd":             "HYD",  "secunderabad": "HYD",
    "chennai":          "MAA",  "madras":          "MAA",
    "kolkata":          "CCU",  "calcutta":        "CCU",
    "pune":             "PNQ",
    "ahmedabad":        "AMD",
    # ── South India ──────────────────────────────────────────────────────────
    "jaipur":           "JAI",  "pink city":       "JAI",
    "kochi":            "COK",  "cochin":          "COK",  "ernakulam": "COK",
    "trivandrum":       "TRV",  "thiruvananthapuram": "TRV", "tvm": "TRV",
    "kozhikode":        "CCJ",  "calicut":         "CCJ",
    "mangalore":        "IXE",  "mangaluru":       "IXE",
    "coimbatore":       "CJB",  "cbe":             "CJB",
    "ooty":             "CJB",  "udhagamandalam":  "CJB",  "coonoor": "CJB",
    "madurai":          "IXM",
    "trichy":           "TRZ",  "tiruchirappalli": "TRZ",
    "tirupati":         "TIR",
    "vijayawada":       "VGA",
    "visakhapatnam":    "VTZ",  "vizag":           "VTZ",
    "pondicherry":      "PNY",  "puducherry":      "PNY",
    "hubli":            "HBX",  "hubballi":        "HBX",
    "belgaum":          "IXG",  "belagavi":        "IXG",
    "mysore":           "MYQ",  "mysuru":          "MYQ",
    "salem":            "SXV",
    "tuticorin":        "TCR",  "thoothukudi":     "TCR",
    "rajahmundry":      "RJA",
    "aurangabad":       "IXU",
    "nashik":           "ISK",  "nasik":           "ISK",
    "kolhapur":         "KLH",
    "solapur":          "SSE",
    "shirdi":           "SAG",
    "kerala":           "COK",
    # ── North India ──────────────────────────────────────────────────────────
    "shimla":           "SLV",
    "manali":           "KUU",  "kullu":           "KUU",
    "dharamsala":       "DHM",  "mcleod ganj":     "DHM",  "mcleodganj": "DHM",
    "dalhousie":        "DHM",  "chamba":          "DHM",  "palampur": "DHM",
    "chandigarh":       "IXC",  "kasauli":         "IXC",
    "dehradun":         "DED",  "rishikesh":       "DED",  "haridwar": "DED",
    "mussoorie":        "DED",  "mussorie":        "DED",
    "jammu":            "IXJ",
    "srinagar":         "SXR",  "gulmarg":         "SXR",  "pahalgam": "SXR",
    "leh":              "IXL",  "ladakh":          "IXL",  "spiti":    "IXL",
    "amritsar":         "ATQ",  "golden temple":   "ATQ",
    "lucknow":          "LKO",
    "varanasi":         "VNS",  "banaras":         "VNS",  "kashi":    "VNS",
    "agra":             "AGR",  "taj mahal":       "AGR",
    "allahabad":        "IXD",  "prayagraj":       "IXD",
    "gorakhpur":        "GOP",
    "kanpur":           "KNU",
    "jodhpur":          "JDH",
    "jaisalmer":        "JSA",
    "udaipur":          "UDR",
    "bikaner":          "BKB",
    "kota":             "KTU",
    "ajmer":            "JAI",
    # ── East India ───────────────────────────────────────────────────────────
    "bhubaneswar":      "BBI",  "puri":            "BBI",  "konark": "BBI",
    "ranchi":           "IXR",
    "patna":            "PAT",
    "gaya":             "GAY",  "bodh gaya":       "GAY",
    "durgapur":         "RDP",
    "darjeeling":       "IXB",  "siliguri":        "IXB",  "bagdogra": "IXB",
    "gangtok":          "IXB",  "sikkim":          "IXB",
    # ── Central India ────────────────────────────────────────────────────────
    "bhopal":           "BHO",
    "indore":           "IDR",
    "gwalior":          "GWL",
    "jabalpur":         "JLR",
    "khajuraho":        "HJR",
    "raipur":           "RPR",
    "nagpur":           "NAG",
    # ── West India ───────────────────────────────────────────────────────────
    "surat":            "STV",
    "rajkot":           "RAJ",
    "bhuj":             "BHJ",
    "jamnagar":         "JGA",
    "porbandar":        "PBD",
    # ── Northeast India ──────────────────────────────────────────────────────
    "guwahati":         "GAU",  "assam":           "GAU",  "kaziranga": "GAU",
    "dibrugarh":        "DIB",
    "jorhat":           "JRH",  "majuli":          "JRH",
    "silchar":          "IXS",
    "tezpur":           "TEZ",
    "shillong":         "SHL",  "meghalaya":       "SHL",  "cherrapunji": "SHL",
    "imphal":           "IMF",  "manipur":         "IMF",
    "agartala":         "IXA",  "tripura":         "IXA",
    "aizawl":           "AJL",  "mizoram":         "AJL",
    "dimapur":          "DMU",  "nagaland":        "DMU",
    "itanagar":         "HGI",  "arunachal":       "HGI",  "tawang": "HGI",
    "pasighat":         "IXT",
    "port blair":       "IXZ",  "andaman":         "IXZ",  "andaman nicobar": "IXZ",
    "lakshadweep":      "AGX",  "agatti":          "AGX",
    # ── International — Middle East ──────────────────────────────────────────
    "dubai":            "DXB",
    "abu dhabi":        "AUH",
    "sharjah":          "SHJ",
    "doha":             "DOH",  "qatar":           "DOH",
    "muscat":           "MCT",  "oman":            "MCT",
    "riyadh":           "RUH",
    "jeddah":           "JED",  "mecca":           "JED",
    "kuwait":           "KWI",
    "bahrain":          "BAH",
    # ── International — Southeast Asia ───────────────────────────────────────
    "singapore":        "SIN",
    "bangkok":          "BKK",  "phuket":          "HKT",  "chiang mai": "CNX",
    "kuala lumpur":     "KUL",  "kl":             "KUL",  "penang":    "PEN",
    "bali":             "DPS",  "denpasar":        "DPS",  "jakarta":   "CGK",
    "ho chi minh":      "SGN",  "saigon":          "SGN",  "hanoi":     "HAN",
    "da nang":          "DAD",
    "phnom penh":       "PNH",  "cambodia":        "PNH",
    "yangon":           "RGN",  "myanmar":         "RGN",
    "manila":           "MNL",  "cebu":            "CEB",
    # ── International — East Asia ─────────────────────────────────────────────
    "hong kong":        "HKG",
    "taipei":           "TPE",  "taiwan":          "TPE",
    "seoul":            "ICN",  "korea":           "ICN",  "busan": "PUS",
    "tokyo":            "NRT",  "osaka":           "KIX",  "fukuoka": "FUK",
    "beijing":          "PEK",  "shanghai":        "PVG",  "guangzhou": "CAN",
    "chengdu":          "CTU",
    # ── International — Europe ────────────────────────────────────────────────
    "london":           "LHR",
    "paris":            "CDG",
    "amsterdam":        "AMS",
    "frankfurt":        "FRA",
    "zurich":           "ZRH",
    "rome":             "FCO",
    "milan":            "MXP",
    "barcelona":        "BCN",  "madrid":          "MAD",
    "vienna":           "VIE",  "prague":          "PRG",
    "budapest":         "BUD",  "brussels":        "BRU",
    "lisbon":           "LIS",  "athens":          "ATH",
    "istanbul":         "IST",  "moscow":          "SVO",
    "stockholm":        "ARN",  "copenhagen":      "CPH",
    "oslo":             "OSL",  "warsaw":          "WAW",
    # ── International — Americas ─────────────────────────────────────────────
    "new york":         "JFK",  "los angeles":     "LAX",
    "chicago":          "ORD",  "san francisco":   "SFO",
    "miami":            "MIA",  "toronto":         "YYZ",  "vancouver": "YVR",
    "mexico city":      "MEX",  "cancun":          "CUN",
    "sao paulo":        "GRU",  "buenos aires":    "EZE",
    "bogota":           "BOG",  "lima":            "LIM",
    # ── International — Oceania & Africa ─────────────────────────────────────
    "sydney":           "SYD",  "melbourne":       "MEL",
    "brisbane":         "BNE",  "perth":           "PER",
    "auckland":         "AKL",
    "johannesburg":     "JNB",  "cape town":       "CPT",
    "nairobi":          "NBO",  "cairo":           "CAI",
    # ── Subcontinent neighbours ───────────────────────────────────────────────
    "colombo":          "CMB",  "sri lanka":       "CMB",
    "kathmandu":        "KTM",  "nepal":           "KTM",  "pokhara": "PKR",
    "dhaka":            "DAC",  "bangladesh":      "DAC",  "chittagong": "CGP",
    "karachi":          "KHI",  "lahore":          "LHE",  "islamabad": "ISB",
    "maldives":         "MLE",  "male":            "MLE",
}

# Tourist spots with no direct airport — maps to nearest hub airport
NEAREST_HUB = {
    # ── Himachal Pradesh ─────────────────────────────────────────────────────
    "kasol":            "DHM",  "kheerganga":     "DHM",  "bir billing": "DHM",
    "barot":            "DHM",  "khajjiar":       "DHM",
    "kufri":            "SLV",  "chail":          "SLV",  "sangla":    "SLV",
    "sarahan":          "SLV",  "kinnaur":        "SLV",  "recong peo": "SLV",
    "solang":           "KUU",  "rohtang":        "KUU",
    "kasauli":          "IXC",
    # ── Uttarakhand ──────────────────────────────────────────────────────────
    "auli":             "DED",  "chopta":         "DED",  "chakrata":  "DED",
    "lansdowne":        "DED",  "kanatal":        "DED",  "dhanaulti": "DED",
    "valley of flowers":"DED",  "hemkund sahib":  "DED",
    "badrinath":        "DED",  "kedarnath":      "DED",
    "gangotri":         "DED",  "yamunotri":      "DED",
    "nainital":         "IXD",  "jim corbett":    "IXD",  "corbett":   "IXD",
    "munsiyari":        "IXD",  "ranikhet":       "IXD",  "almora":    "IXD",
    # ── J&K / Ladakh ─────────────────────────────────────────────────────────
    "pangong":          "IXL",  "nubra valley":   "IXL",  "zanskar":   "IXL",
    "kargil":           "IXL",  "turtuk":         "IXL",  "hanle":     "IXL",
    "gurez":            "SXR",  "sonamarg":       "SXR",  "yusmarg":   "SXR",
    "betaab valley":    "SXR",
    # ── Rajasthan tourist spots ───────────────────────────────────────────────
    "ranthambore":      "JAI",  "pushkar":        "JAI",  "bundi":     "JAI",
    "sawai madhopur":   "JAI",  "abhaneri":       "JAI",  "samode":    "JAI",
    "bharatpur":        "AGR",  "kumbhalgarh":    "UDR",  "chittorgarh": "UDR",
    "mount abu":        "UDR",  "nathdwara":      "UDR",
    # ── Madhya Pradesh ───────────────────────────────────────────────────────
    "orchha":           "GWL",  "gwalior fort":   "GWL",  "shivpuri":  "GWL",
    "ujjain":           "IDR",  "omkareshwar":    "IDR",  "mandu":     "IDR",
    "kanha":            "JLR",  "bandhavgarh":    "JLR",  "pench":     "NAG",
    "pachmarhi":        "BHO",  "sanchi":         "BHO",
    "khajuraho":        "HJR",  "satna":          "TNI",
    # ── Maharashtra ──────────────────────────────────────────────────────────
    "mahabaleshwar":    "PNQ",  "lonavala":       "PNQ",  "panchgani": "PNQ",
    "kolad":            "PNQ",  "lavasa":         "PNQ",  "igatpuri":  "BOM",
    "matheran":         "BOM",  "alibaug":        "BOM",  "kashid":    "BOM",
    "tadoba":           "NAG",  "ajanta":         "IXU",  "ellora":    "IXU",
    "melghat":          "NAG",
    # ── Karnataka ────────────────────────────────────────────────────────────
    "coorg":            "BLR",  "chikmagalur":    "BLR",  "sakleshpur":"BLR",
    "kabini":           "BLR",  "nagarhole":      "BLR",  "bandipur":  "BLR",
    "shivamogga":       "BLR",  "shimoga":        "BLR",
    "kudremukh":        "IXE",  "murudeshwar":    "IXE",  "karwar":    "IXE",
    "udupi":            "IXE",  "gokarna":        "IXE",  "yana":      "IXE",
    "hampi":            "HBX",  "hospet":         "HBX",  "badami":    "HBX",
    "aihole":           "HBX",  "pattadakal":     "HBX",  "dandeli":   "HBX",
    "jog falls":        "HBX",
    "mysore":           "MYQ",  "mysuru":         "MYQ",
    # ── Kerala ───────────────────────────────────────────────────────────────
    "munnar":           "COK",  "thekkady":       "COK",  "idukki":    "COK",
    "alleppey":         "COK",  "alappuzha":      "COK",  "athirapally": "COK",
    "vagamon":          "COK",  "peermade":       "COK",
    "wayanad":          "CCJ",  "bekal":          "CCJ",  "thrissur":  "CCJ",
    "varkala":          "TRV",  "kovalam":        "TRV",  "ponmudi":   "TRV",
    "parambikulam":     "CJB",  "silent valley":  "CJB",
    # ── Tamil Nadu ───────────────────────────────────────────────────────────
    "kodaikanal":       "IXM",  "rameswaram":     "IXM",  "ramnad":    "IXM",
    "kanyakumari":      "TRV",
    "yercaud":          "SXV",  "kolli hills":    "TRZ",
    "topslip":          "CJB",  "valparai":       "CJB",  "pollachi":  "CJB",
    "hogenakkal":       "MAA",  "yelagiri":       "MAA",  "mahabalipuram": "MAA",
    # ── Andhra Pradesh ───────────────────────────────────────────────────────
    "araku":            "VTZ",  "lambasingi":     "VTZ",  "horsley hills": "TIR",
    "nagarjunasagar":   "HYD",
    # ── UP / Pilgrimages ─────────────────────────────────────────────────────
    "vrindavan":        "AGR",  "mathura":        "AGR",  "fatehpur sikri": "AGR",
    "ayodhya":          "LKO",  "chitrakoot":     "IXD",
    # ── Odisha ───────────────────────────────────────────────────────────────
    "konark":           "BBI",  "chilika":        "BBI",  "gopalpur":  "BBI",
    "simlipal":         "BBI",  "bhitarkanika":   "BBI",  "puri":      "BBI",
    # ── West Bengal ──────────────────────────────────────────────────────────
    "sundarbans":       "CCU",  "digha":          "CCU",  "mandarmani": "CCU",
    "shantiniketan":    "CCU",  "bishnupur":      "CCU",
    # ── Northeast tourist spots ───────────────────────────────────────────────
    "manas":            "GAU",  "kaziranga":      "GAU",  "hajo":      "GAU",
    "shillong peaks":   "SHL",  "dawki":          "SHL",  "mawlynnong":"SHL",
    "dzukou":           "DMU",  "loktak lake":    "IMF",
    "ziro":             "HGI",  "mechuka":        "IXT",
    "namdapha":         "DIB",
    # ── Gujarat ──────────────────────────────────────────────────────────────
    "gir":              "RAJ",  "somnath":        "RAJ",  "dwarka":    "RAJ",
    "saputara":         "STV",  "rann of kutch":  "BHJ",  "kutch":     "BHJ",
    "palitana":         "BHJ",  "diu":            "DIU",
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

    # ── Budget guard: skip flights when budget is too low ──────────────────────
    if budget < 3000:
        return {"flights": f"  ⚠️  Budget too low for flights (₹{budget:,.0f}). Consider train or bus travel instead."}

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

        
        lines = []
        for i, offer in enumerate(top3, 1):
            if i > 1: break
            seg      = offer["itineraries"][0]["segments"][0]
            carrier  = seg["carrierCode"]
            airline  = AIRLINE_NAMES.get(carrier, carrier)
            duration = _format_duration(offer["itineraries"][0]["duration"])
            price    = float(offer["price"]["grandTotal"])

            lines.append(f"{origin_iata} → {dest_iata}")
            lines.append(f"Airline : {airline}")
            lines.append(f"Duration : {duration}")
            lines.append(f"Price : ₹{int(price):,}")

        return {"flights": "\n".join(lines)}

    except Exception as e:
        return {"flights": f"Flight search failed: {e}"}
