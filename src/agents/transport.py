"""
transport.py — Transport Agent
"""

import os
import json
import urllib.parse
import requests
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_groq import ChatGroq

load_dotenv()

_TAVILY_KEY = os.getenv("TAVILY_API_KEY", "").strip()
_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

def geocode_nominatim(query: str) -> tuple[float, float]:
    """Return (lon, lat) using Nominatim, or None on failure."""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1"
        headers = {"User-Agent": "TravelPlannerApp/2.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                lat = float(data[0].get("lat"))
                lon = float(data[0].get("lon"))
                return lon, lat
    except:
        pass
    return None

def get_osrm_route(lon1: float, lat1: float, lon2: float, lat2: float) -> tuple[float, float]:
    """Return (distance_km, duration_hours) using OSRM, or None on failure."""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            routes = data.get("routes", [])
            if routes:
                dist_m = routes[0].get("distance", 0)
                dur_s = routes[0].get("duration", 0)
                return (dist_m / 1000.0), (dur_s / 3600.0)
    except:
        pass
    return None

def transport_agent(state: dict) -> dict:
    destination = state.get("destination", "")
    origin = state.get("origin") or "major cities"
    final_transport = "Transport information unavailable."
    dest_iata = None

    if not destination or destination == "Unknown":
        return {"transport": final_transport, "destination_iata": dest_iata}

    try:
        client = TavilyClient(api_key=_TAVILY_KEY)
        
        # 1. Airport Search
        air_q = f"nearest commercial airport to {destination} India with 3-letter IATA code"
        air_res = client.search(air_q, max_results=2)
        air_text = " ".join([r.get("content", "") for r in air_res.get("results", [])])

        # 2. Railway Station Search
        train_q = f"nearest railway station to {destination}"
        train_res = client.search(train_q, max_results=2)
        train_text = " ".join([r.get("content", "") for r in train_res.get("results", [])])

        # 3. Bus Operators
        bus_q = f"bus operators and services from {origin} to {destination} India"
        bus_res = client.search(bus_q, max_results=2)
        bus_text = " ".join([r.get("content", "") for r in bus_res.get("results", [])])

        # 4. Road Distance (OSRM + Fallback)
        road_text = ""
        c1 = geocode_nominatim(origin)
        c2 = geocode_nominatim(destination)
        if c1 and c2:
            route = get_osrm_route(c1[0], c1[1], c2[0], c2[1])
            if route:
                dist_km, dur_h = route
                h = int(dur_h)
                m = int((dur_h - h) * 60)
                road_text = f"OSRM Routing: {dist_km:.1f} km, {h}h {m}m driving time. Primary Route: NH highways."
        
        if not road_text:
            road_q = f"driving distance and time from {origin} to {destination} by road"
            road_res = client.search(road_q, max_results=2)
            road_text = " ".join([r.get("content", "") for r in road_res.get("results", [])])

        combined_text = f"Air context: {air_text}\nTrain context: {train_text}\nBus context: {bus_text}\nRoad context: {road_text}"

        if _GROQ_KEY:
            llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
            prompt = (
                f"You are a travel assistant extracting transport data from {origin} to {destination}.\n\n"
                f"First, on the very first line, output strictly: [IATA: XYZ] where XYZ is the 3-letter IATA code of the nearest commercial airport. If unknown, [IATA: Unknown].\n"
                f"Then, starting on the next line, output the exact transport text matching the template below.\n\n"
                f"Template:\n"
                f"✈ By Air\n"
                f"Nearest Airport : Extract airport name and IATA code\n"
                f"Distance : Extract approx distance to destination\n\n"
                f"🚆 By Train\n"
                f"Nearest Stations:\n"
                f"• Extract station 1 - distance\n"
                f"• Extract station 2 - distance\n\n"
                f"Connectivity:\n"
                f"Extract where direct trains connect from.\n\n"
                f"🚌 By Bus\n"
                f"Operators:\n"
                f"• Operator 1\n"
                f"• Operator 2\n\n"
                f"🚗 By Road\n"
                f"{origin} → {destination}\n"
                f"Distance : Extract total distance\n"
                f"Driving time : Extract total travel time\n"
                f"Route : Extract primary highway or route if available\n\n"
                f"Rules:\n"
                f"- Never use bolding asterisks `**`.\n"
                f"- Do not use 'Not specified' if context implies an answer.\n"
                f"- Base all details on the Context data below.\n\n"
                f"Context data:\n{combined_text}"
            )
            res = llm.invoke(prompt)
            content = res.content.strip()
            
            import re
            iata_match = re.search(r"\[IATA:\s*([A-Z]{3}|Unknown)\]", content, re.IGNORECASE)
            if iata_match:
                extracted = iata_match.group(1).upper()
                if extracted != "UNKNOWN":
                    dest_iata = extracted
                # Remove the IATA tag block from the final markdown
                final_transport = re.sub(r"\[IATA:[^\]]+\]", "", content).strip()
            else:
                final_transport = content

            return {"transport": final_transport, "destination_iata": dest_iata}
            
        return {"transport": "Transport information unavailable.", "destination_iata": None}

    except Exception as e:
        print(f"Transport search failed: {e}")
        return {"transport": "Transport information unavailable (error).", "destination_iata": None}
