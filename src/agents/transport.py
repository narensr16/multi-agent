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

    if not destination or destination == "Unknown":
        return {"transport": "Transport search skipped: destination unknown."}
    if not _TAVILY_KEY:
        return {"transport": "Transport search skipped: TAVILY_API_KEY not configured."}

    transport_text = "By Air : Nearest Airport"

    try:
        client = TavilyClient(api_key=_TAVILY_KEY)
        q = f"how to reach {destination} by flight nearest airport name"
        res = client.search(q, max_results=3)
        parts = [res.get("answer") or ""] + [r.get("content") or "" for r in res.get("results", [])]
        combined = " ".join(parts)

        if _GROQ_KEY and _GROQ_KEY != "your_groq_api_key_here":
            llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
            prompt = (
                f"Based on the text below, identify the primary transport mode (e.g., By Air, By Train) and the name of the main station/airport to reach {destination}.\n"
                f"Keep it extremely concise, to exactly 1 line matching this format exactly: 'By Air : Singapore Changi Airport (SIN)'.\n"
                f"Text: {combined}"
            )
            res = llm.invoke(prompt)
            transport_text = res.content.strip()

    except Exception:
        pass

    return {"transport": transport_text}
