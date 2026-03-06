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

def transport_agent(state: dict) -> dict:
    destination = state.get("destination", "")

    origin = state.get("origin") or "major cities"
    final_transport = "Transport information unavailable."

    try:
        client = TavilyClient(api_key=_TAVILY_KEY)
        # Search specifically for the route from origin to destination
        q_route = f"how to reach {destination} from {origin} by air, train, bus, and road. Include distances and travel times."
        res_route = client.search(q_route, max_results=5)
        
        route_chunks = [res_route.get("answer") or ""] + [r.get("content") or "" for r in res_route.get("results", [])]
        combined_text = " ".join(route_chunks)

        if _GROQ_KEY:
            llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
            prompt = (
                f"Identify real transport options from {origin} to {destination} based on the text.\n"
                f"You MUST include these sections with emojis:\n"
                f"✈ By Air (Nearest commercial airport to {destination}, its IATA code, and approx distance from that airport to {destination})\n"
                f"🚆 By Train (Primary railway station and connectivity types)\n"
                f"🚌 By Bus (Primary bus hub or state transport details)\n"
                f"🚗 By Road (Origin → Destination, Distance in km, and approx Travel time)\n\n"
                f"Structure the output exactly like this:\n"
                f"✈ By Air\nNearest Airport to {destination} : ...\nDistance to {destination} : ...\n\n🚆 By Train\n...\n\n🚌 By Bus\n...\n\n🚗 By Road\n{origin} → {destination}\nDistance : ...\nTravel time : ...\n\n"
                f"Text: {combined_text}"
            )
            res = llm.invoke(prompt)
            final_transport = res.content.strip()
            return {"transport": final_transport}
            
        return {"transport": "Transport information unavailable."}

    except Exception as e:
        print(f"Transport search failed: {e}")
        return {"transport": "Transport information unavailable."}

    except Exception as e:
        print(f"Transport search failed: {e}")
        return {"transport": "Transport information unavailable."}
