"""
hotel.py — Hotel Agent
Searches Tavily for hotels at the destination and the average price per night.
"""

import os
import json
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_groq import ChatGroq

load_dotenv()

_TAVILY_KEY = os.getenv("TAVILY_API_KEY", "").strip()
_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

def hotel_agent(state: dict) -> dict:
    destination = state.get("destination", "")

    if not destination or destination == "Unknown":
        return {"hotels": ["Hotel search skipped: destination unknown."], "hotel_price_raw": "Unknown"}
    if not _TAVILY_KEY:
        return {"hotels": ["Hotel search skipped: TAVILY_API_KEY not configured."], "hotel_price_raw": "Unknown"}

    hotels = []
    hotel_price_raw = "Unknown"

    try:
        client = TavilyClient(api_key=_TAVILY_KEY)
        q1 = f"List 5 specific real popular hotels in {destination} with their current nightly room rates"
        res1 = client.search(q1, max_results=6)
        
        chunks = [res1.get("answer") or ""] + [r.get("content") or "" for r in res1.get("results", [])]
        combined_text = " ".join(chunks)

        # Extract average hotel cost directly from Tavily results if possible
        if res1.get("answer"):
            # A simple heuristic to find a price in the answer
            import re
            price_match = re.search(r'(\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+\s*(?:USD|EUR|GBP|JPY|AUD|CAD|CHF|CNY|SEK|NZD|SGD|HKD|NOK|KRW|INR|BRL|ZAR|MXN|RUB|TRY|IDR|MYR|PHP|THB|VND|PLN|DKK|HUF|CZK|ILS|CLP|COP|PEN|ARS|AED|QAR|SAR|KWD|BHD|OMR|LKR|PKR|BDT|NPR|LAK|KHR|MMK|MNT|UZS|KZT|GEL|AZN|AMD|BYN|UAH|MDL|RSD|MKD|BAM|ALL|HRK|BGN|RON|ISK|FJD|PGK|SBD|VUV|WST|TOP|KMF|DJF|ERN|ETB|GHS|GMD|GNF|KES|LRD|LSL|MAD|MGA|MRO|MUR|MWK|MZN|NAD|NGN|RWF|SCR|SDG|SLL|SOS|SSP|STD|SZL|TND|TZS|UGX|XAF|XCD|XOF|XPF|ZMW|ZWL|AFN|DZD|AOA|XCD|AWG|AZN|BHD|BBD|BYN|BZD|BMD|BTN|BOB|BWP|BND|BGN|BIF|CVE|KHR|KYD|CDF|CLP|CNY|COP|KMF|CRC|HRK|CUP|CZK|DKK|DJF|DOP|EGP|SVC|ERN|ETB|FKP|FJD|GMD|GEL|GIP|GTQ|GNF|GYD|HTG|HNL|HUF|ISK|IDR|IRR|IQD|JMD|JOD|KZT|KES|KWD|KGS|LAK|LBP|LSL|LRD|LYD|MOP|MKD|MGA|MWK|MYR|MVR|MRU|MUR|MXN|MDL|MNT|MAD|MZN|MMK|NAD|NPR|NIO|NGN|OMR|PKR|PAB|PGK|PYG|PEN|PHP|PLN|QAR|RON|RUB|RWF|SHP|SAR|RSD|SCR|SLL|SGD|SBD|SOS|ZAR|KRW|SSP|LKR|SDG|SRD|SZL|SEK|CHF|SYP|TWD|TJS|TZS|THB|TOP|TTD|TND|TRY|TMT|UGX|UAH|AED|UYU|UZS|VND|XPF|YER|ZMW)\b)', res1["answer"])
            if price_match:
                hotel_price_raw = price_match.group(0).strip()
        
        # Fallback to LLM if direct extraction is difficult or not found, or if no direct answer was available
        if (not res1.get("answer") or hotel_price_raw == "Unknown") and _GROQ_KEY and _GROQ_KEY != "your_groq_api_key_here":
            llm = ChatGroq(api_key=_GROQ_KEY, model_name="llama-3.1-8b-instant", temperature=0)
            prompt = (
                f"Extract up to 5 ACTUAL, REAL SPECIFIC hotels in {destination} from the text below.\n"
                f"Ignore generic headers like '5-star hotel', 'cheap hotel', 'luxury stay'. We need REAL NAMES (e.g., 'Grand Hyatt Kochi', 'The Tamara Coorg').\n"
                f"For EACH hotel, extract its individual nightly price (e.g., 'SGD 200', '$150', '₹5000').\n"
                f"IMPORTANT: If the destination is in India, PRIORITIZE prices in INR (₹). If you see symbols like 'C$' or 'A$' for an Indian hotel, it is likely a scraping error; try to find the INR price or use the raw number as INR if it seems like a local rate.\n"
                f"Return ONLY a raw JSON dictionary with a single key 'hotel_data' which is a list of objects.\n"
                f'Example: {{"hotel_data": [{{"name": "Marina Bay Sands", "price": "SGD 800"}}, {{"name": "Hotel Boss", "price": "SGD 150"}}]}}\n'
                f"Text: {combined_text}"
            )
            res = llm.invoke(prompt)
            content = res.content.strip()
            # Clean up potential markdown or junk
            if "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            
            try:
                parsed = json.loads(content.strip())
            except json.JSONDecodeError:
                # If JSON fails, the return dict below will trigger fallback
                parsed = {}
            
            hotel_data = parsed.get("hotel_data", [])
            if isinstance(hotel_data, list) and hotel_data:
                valid_prices = []
                display_hotels = []
                currency_symbol = ""

                import re
                for item in hotel_data:
                    name = str(item.get("name", "")).strip()
                    price_str = str(item.get("price", "")).strip()
                    if not name or len(name) < 3: continue
                    
                    # Extract numeric part
                    nums = re.findall(r"[\d,]+(?:\.\d+)?", price_str)
                    if nums:
                        val = float(nums[0].replace(",", ""))
                        valid_prices.append(val)
                        display_hotels.append(f"{name} ({price_str})")
                        
                        # Grab currency symbol from the first valid price
                        if not currency_symbol:
                            # Try to find symbol (non-numeric, non-whitespace)
                            sym_match = re.search(r"[^\d\s\.,]+", price_str)
                            if sym_match:
                                currency_symbol = sym_match.group(0)

                if valid_prices:
                    avg_val = sum(valid_prices) / len(valid_prices)
                    # Format as string for budget agent
                    hotel_price_raw = f"{currency_symbol}{base_round(avg_val)}" if currency_symbol else str(base_round(avg_val))
                    hotels = display_hotels[:5]

    except Exception as e:
        print(f"Hotel search failed: {e}")
        pass

    hotels = hotels[:5]
    if not hotels:
        hotels = [f"{destination} Grand Hotel", f"{destination} Central Resort", f"The {destination} Inn"]

    if not hotel_price_raw or hotel_price_raw == "Unknown":
        hotel_price_raw = "$100"

    return {
        "hotels": hotels,
        "hotel_price_raw": hotel_price_raw
    }

def base_round(x):
    return round(float(x), 2)
