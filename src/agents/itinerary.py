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

    itinerary_data = []
    
    if _TAVILY_KEY:
        try:
            client = TavilyClient(api_key=_TAVILY_KEY)
            map_places = []
            # Search for top attractions and their fees
            q1 = f"Top tourist attractions in {destination} with entrance fees 2026 and descriptions"
            res1 = client.search(q1, max_results=10)
            
            chunks = [res1.get("answer") or ""] + [r.get("content") or "" for r in res1.get("results", [])]
            combined_text = " ".join(chunks)

            if _GROQ_KEY and _GROQ_KEY != "your_groq_api_key_here":
                llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
                
                # Get exchange rate logic from state or baseline
                # For simplicity, we'll assume the budget agent handles the final INR conversion, 
                # but we'll extract the fee in original and attempt to provide a numeric value.
                
                prompt = (
                f"Create a {days}-day travel itinerary for {destination}.\n"
                f"CRITICAL: Keep travel realistic! Group attractions logically by geographic proximity each day. Do not make the user criss-cross the city or region.\n"
                f"For EACH DAY, you MUST provide exactly 3 slots: Morning, Afternoon, and Evening.\n"
                f"For EACH slot, provide:\n"
                f"1. A specific attraction or activity name (e.g., 'Merlion Park')\n"
                f"2. The typical entrance fee in local currency (e.g., 'SGD 20' or 'Free')\n\n"
                f"Return ONLY a raw JSON dictionary with key 'itinerary'.\n"
                f'Example: {{"itinerary": [{{"day": 1, "morning": {{"name": "...", "fee": "..."}}, "afternoon": {{"name": "...", "fee": "..."}}, "evening": {{"name": "...", "fee": "..."}}}}]}}\n'
                f"Text: {combined_text}"
            )
            res = llm.invoke(prompt)
            content = res.content.strip()
            if "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            
            itinerary_data = json.loads(content).get("itinerary", [])
            lines = []
            total_activities_cost_inr = 0.0

            for day_obj in itinerary_data:
                d_num = day_obj.get("day", "?")
                lines.append(f"Day {d_num}")
                
                for slot in ["morning", "afternoon", "evening"]:
                    item = day_obj.get(slot, {})
                    name = item.get("name", "Relax")
                    fee_str = item.get("fee", "Free")
                    
                    # Store for map section
                    map_places.append(f"{name} ({destination})")
                    
                    lines.append(f"  {slot.capitalize()}: {name} ({fee_str})")
                    
                    # Numeric fee extraction
                    import re
                    nums = re.findall(r"[\d,]+(?:\.\d+)?", fee_str)
                    if nums:
                        val = float(nums[0].replace(",", ""))
                        curr_match = re.search(r"[A-Z]{3}|[₹$€£]", fee_str)
                        curr_sym = curr_match.group(0) if curr_match else "INR"
                        
                        # Map symbol to code for FX lookup
                        symbol_map = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "S$": "SGD", "AED": "AED"}
                        curr_code = curr_sym
                        if curr_sym in symbol_map:
                            curr_code = symbol_map[curr_sym]
                        
                        rate = get_exchange_rate_to_inr(curr_code)
                        total_activities_cost_inr += (val * rate)

            return {
                "itinerary": "\n".join(lines),
                "activities_cost": round(total_activities_cost_inr, 2),
                "map_places": map_places[:15]
            }

        except Exception as e:
            print(f"Itinerary search failed: {e}")
            return {"itinerary": "Itinerary unavailable.", "activities_cost": 0.0}

    if not itinerary_data:
        # Fallback basic structure
        itinerary_data = []
        for d in range(1, days + 1):
            itinerary_data.append({
                "day": d,
                "morning": {"name": "Local Landmarks", "fee": "Free"},
                "afternoon": {"name": "Central Museum", "fee": "Unknown"},
                "evening": {"name": "City Walk / Dinner", "fee": "Free"}
            })

    total_activities_cost = 0.0
    lines = []
    
    for day_obj in itinerary_data:
        d = day_obj.get("day", "?")
        lines.append(f"Day {d}")
        
        for slot in ["morning", "afternoon", "evening"]:
            item = day_obj.get(slot, {})
            name = item.get("name", "Rest")
            raw_fee = item.get("fee", "Free")
            
            inr_val, display_fee = parse_fee_to_inr(raw_fee, c_code, fx_rate)
            total_activities_cost += inr_val
            
            lines.append(f"  {slot.capitalize()}: {name} ({display_fee})")
            
        lines.append("") # Blank line after each day
        
    total_activities_cost = round(total_activities_cost / 100) * 100

    return {
        "itinerary": "\n".join(lines).strip(),
        "activities_cost": total_activities_cost
    }
