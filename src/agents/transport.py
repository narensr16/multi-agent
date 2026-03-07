"""
transport.py — Transport Agent
"""

import os
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_groq import ChatGroq

load_dotenv()

_TAVILY_KEY = os.getenv("TAVILY_API_KEY", "").strip()
_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

import urllib.parse
import requests

def get_airport_from_nominatim(destination: str) -> str:
    """Fallback to Nominatim if Tavily isn't explicitly used for air."""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q=airport+near+{urllib.parse.quote(destination)}&format=json&limit=1"
        headers = {"User-Agent": "TravelPlannerApp/1.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                name = data[0].get("name", "Unknown Airport")
                return name
    except:
        pass
    return "Not specified"

def transport_agent(state: dict) -> dict:
    destination = state.get("destination", "")
    origin = state.get("origin") or "major cities"
    final_transport = "Transport information unavailable."

    if not destination or destination == "Unknown":
        return {"transport": final_transport}

    try:
        client = TavilyClient(api_key=_TAVILY_KEY)
        
        # 1. Airport Search
        air_q = f"nearest airport to {destination} India"
        air_res = client.search(air_q, max_results=2)
        air_text = " ".join([r.get("content", "") for r in air_res.get("results", [])])

        # 2. Railway Station Search
        train_q = f"nearest railway station to {destination}"
        train_res = client.search(train_q, max_results=2)
        train_text = " ".join([r.get("content", "") for r in train_res.get("results", [])])

        # 3. Bus Connectivity
        bus_q = f"bus connectivity to {destination} Karnataka India"
        bus_res = client.search(bus_q, max_results=2)
        bus_text = " ".join([r.get("content", "") for r in bus_res.get("results", [])])

        # 4. Road Distance
        road_q = f"distance from {origin} to {destination} by road"
        road_res = client.search(road_q, max_results=2)
        road_text = " ".join([r.get("content", "") for r in road_res.get("results", [])])

        combined_text = f"Air context: {air_text}\nTrain context: {train_text}\nBus context: {bus_text}\nRoad context: {road_text}"

        if _GROQ_KEY:
            llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
            prompt = (
                f"You are a travel assistant extracting transport data from {origin} to {destination}.\n"
                f"Based on the text context provided, formulate the transport options EXACTLY in this plain text format, keeping the spacing and bullet styles identical.\n"
                f"Do not use 'Not specified' or 'Unknown' if the context implies an answer. Do not use Markdown header tags like `###` or `####` and NEVER use bolding asterisks `**`.\n\n"
                f"✈ By Air\n"
                f"Nearest Airport : Extract airport name and IATA code\n"
                f"Distance : Extract approx distance to destination\n\n"
                f"🚆 By Train\n"
                f"Nearest Stations :\n"
                f"• Extract station 1 - distance\n"
                f"• Extract station 2 - distance\n\n"
                f"Connectivity :\n"
                f"Extract where direct trains connect from.\n\n"
                f"🚌 By Bus\n\n"
                f"Extract operators and routes like:\n"
                f"• Point A → Point B\n"
                f"• Point C → Point B\n\n"
                f"🚗 By Road\n\n"
                f"Origin → Destination (replace with actual cities)\n"
                f"Distance : Extract total distance\n"
                f"Travel time : Extract total travel time\n\n"
                f"---\n"
                f"Context data:\n{combined_text}"
            )
            res = llm.invoke(prompt)
            final_transport = res.content.strip()
            
            # Remove any markdown code block wrappers if Groq added them
            if final_transport.startswith("```"):
                final_transport = "\n".join(final_transport.split("\n")[1:-1]).strip()

            return {"transport": final_transport}
            
        return {"transport": "Transport information unavailable."}

    except Exception as e:
        print(f"Transport search failed: {e}")
        return {"transport": "Transport information unavailable (error)."}
