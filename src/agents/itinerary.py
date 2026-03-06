"""
itinerary.py — Day-by-Day Itinerary Agent
Extracts attractions and entry fees, converting them to INR using budget.py's FX rate.
Writes: itinerary (str), activities_cost (float)
"""
import os
import re
import json
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_groq import ChatGroq

from agents.budget import detect_country_and_currency, get_exchange_rate_to_inr

load_dotenv()
_TAVILY_KEY = os.getenv("TAVILY_API_KEY", "").strip()
_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

def parse_fee_to_inr(fee_str: str, dest_currency_code: str, fx_rate: float) -> tuple[float, str]:
    if not fee_str or fee_str.lower() in ["free", "unknown", "varies", "none", "n/a", ""]:
        return 0.0, fee_str
        
    nums = re.findall(r"[\d,]+(?:\.\d+)?", fee_str)
    if not nums:
        return 0.0, fee_str
        
    val = float(nums[0].replace(",", ""))
    
    if "₹" in fee_str or "inr" in fee_str.lower():
        return val, f"₹{int(val)}"
        
    if dest_currency_code == "INR" and "$" not in fee_str and "€" not in fee_str:
        return val, f"₹{int(val)}"
        
    inr_val = val * fx_rate
    return inr_val, f"₹{int(inr_val)}"

def itinerary_agent(state: dict) -> dict:
    destination = state.get("destination", "")
    days = state.get("days", 3)
    try: days = int(days)
    except: days = 3
    
    if not destination or destination == "Unknown":
        return {"itinerary": "Itinerary skipped.", "activities_cost": 0.0}

    country, c_code, c_sym = detect_country_and_currency(destination)
    fx_rate = get_exchange_rate_to_inr(c_code)

    attractions = []
    
    if _TAVILY_KEY:
        try:
            client = TavilyClient(api_key=_TAVILY_KEY)
            query = f"top tourist attractions places to visit in {destination} entrance fees ticket prices 2026"
            result = client.search(query, max_results=6)
            
            combined = " ".join([r.get("content", "") for r in result.get("results", [])])

            if _GROQ_KEY and _GROQ_KEY != "your_groq_api_key_here":
                llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
                prompt = (
                    f"Extract up to {days * 3} real tourist attractions in {destination}.\n"
                    f"Also extract the EXACT ticket price/entrance fee for each attraction, INCLUDING the currency symbol (like $292, SGD 28, €10, ¥1000, ₹500).\n"
                    f"If fee is not mentioned, use 'Unknown'. If free, use 'Free'.\n"
                    f"Return ONLY a raw JSON list of objects with keys 'name' and 'fee'. Avoid conversational text.\n\n"
                    f"Text: {combined}"
                )
                res = llm.invoke(prompt)
                content = res.content.strip()
                if content.startswith("```json"): content = content[7:-3]
                elif content.startswith("```"):   content = content[3:-3]
                
                parsed = json.loads(content.strip())
                if isinstance(parsed, list):
                    for a in parsed:
                        name = str(a.get("name", "")).strip()
                        fee = str(a.get("fee", "Unknown")).strip()
                        if len(name) > 3:
                            attractions.append({"name": name, "raw_fee": fee})
        except Exception:
            pass

    if len(attractions) < days * 2:
        fb = ["City Center", "Local Market", "Main Museum", "Central Park", "Old Town", "Heritage Village"]
        for item in fb:
            if item not in [a["name"] for a in attractions]:
                attractions.append({"name": item, "raw_fee": "Unknown"})

    total_activities_cost = 0.0
    lines = []
    idx = 0
    
    for d in range(1, days + 1):
        lines.append(f"Day {d}")
        day_items = attractions[idx : idx + 2] if d == 1 else attractions[idx : idx + 3]
        if not day_items and d > 1:
            day_items = attractions[:2] 
        idx += len(day_items)
        
        for item in day_items:
            name = item["name"]
            raw_fee = item.get("raw_fee", "Unknown")
            
            inr_val, display_fee = parse_fee_to_inr(raw_fee, c_code, fx_rate)
            total_activities_cost += inr_val
            
            lines.append(name)
            
        lines.append("") # Blank line after each day
        
    total_activities_cost = round(total_activities_cost / 100) * 100

    return {
        "itinerary": "\n".join(lines).strip(),
        "activities_cost": total_activities_cost
    }
