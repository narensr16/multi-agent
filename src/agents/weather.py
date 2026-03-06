"""
weather.py — Weather Agent

Primary  : WeatherAPI (weatherapi.com) — requires WEATHER_API_KEY in .env
Fallback : Tavily internet search — works even without the WeatherAPI key

Get a FREE WeatherAPI key at: https://www.weatherapi.com/signup.aspx
(1 million calls/month, no credit card required)
"""

import os
import re
import requests
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "").strip()
TAVILY_API_KEY  = os.getenv("TAVILY_API_KEY",  "").strip()


# ──────────────────────────────────────────────────────────────────────────────
# Primary: WeatherAPI
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_from_weatherapi(destination: str) -> str | None:
    """Return formatted current weather string or None on any failure."""
    if not WEATHER_API_KEY or WEATHER_API_KEY == "your_weatherapi_key_here":
        return None

    try:
        url = (
            f"http://api.weatherapi.com/v1/current.json"
            f"?key={WEATHER_API_KEY}&q={destination}&aqi=no"
        )
        resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            return None

        data = resp.json()
        if "current" not in data:
            return None

        current   = data["current"]
        temp      = current.get("temp_c", "N/A")
        feels     = current.get("feelslike_c", "N/A")
        condition = current.get("condition", {}).get("text", "N/A")
        humidity  = current.get("humidity", "N/A")
        wind      = current.get("wind_kph", "N/A")

        return (
            f"Temperature : {temp}°C\n"
            f"Condition : {condition}"
        )

    except Exception:
        return None


def _fetch_forecast_from_weatherapi(destination: str) -> str | None:
    """Return 3-day forecast string or None on failure."""
    if not WEATHER_API_KEY or WEATHER_API_KEY == "your_weatherapi_key_here":
        return None

    try:
        url = (
            f"http://api.weatherapi.com/v1/forecast.json"
            f"?key={WEATHER_API_KEY}&q={destination}&days=3&aqi=no&alerts=no"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None

        data = resp.json()
        forecast_days = data.get("forecast", {}).get("forecastday", [])
        if not forecast_days:
            return None

        _COND_ICON = {
            "sunny": "☀️", "clear": "☀️", "partly cloudy": "⛅",
            "cloudy": "☁️", "overcast": "☁️", "rain": "🌧️",
            "drizzle": "🌧️", "thunderstorm": "⚡", "snow": "❄️",
            "fog": "🌫️", "mist": "🌫️",
        }

        lines = []
        for day in forecast_days:
            date_str = day.get("date", "")            # '2026-03-06'
            day_data = day.get("day", {})
            max_c    = day_data.get("maxtemp_c", "?")
            min_c    = day_data.get("mintemp_c", "?")
            cond     = day_data.get("condition", {}).get("text", "")
            icon     = next((v for k, v in _COND_ICON.items() if k in cond.lower()), "🌤️")
            # Format date as 'Thu 06 Mar'
            try:
                from datetime import datetime
                d = datetime.strptime(date_str, "%Y-%m-%d")
                date_label = d.strftime("%a %d %b")
            except Exception:
                date_label = date_str
            lines.append(f"  {date_label} : {icon} {max_c}°C / {min_c}°C — {cond}")

        return "\n".join(lines) if lines else None

    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Fallback: Tavily web search
# ──────────────────────────────────────────────────────────────────────────────

def _fetch_from_tavily(destination: str) -> str:
    """Use Tavily to get current weather info when WeatherAPI key is absent."""
    if not TAVILY_API_KEY:
        return "Weather data unavailable (no API keys configured)."

    try:
        client  = TavilyClient(api_key=TAVILY_API_KEY)
        query   = f"current weather in {destination} India today temperature humidity"
        result  = client.search(query, max_results=3)

        snippets = []
        for r in result.get("results", []):
            content = r.get("content", "").strip()
            if content:
                snippets.append(content)

        if not snippets:
            return f"Weather data not found for {destination}."

        # Try to pull out temperature with a regex from the combined text
        combined = " ".join(snippets[:3])
        temp_match = re.search(r"(?:temp(?:erature)?.*?|)(\d{1,3})\s*(?:°|degrees?|deg)?\s*[CF]\b", combined, re.IGNORECASE)
        if not temp_match:
            temp_match = re.search(r"\b(\d{1,2})\s*°", combined)
            
        humid_match = re.search(r"humidity\s*[:\-]?\s*(\d{1,3})\s*%", combined, re.IGNORECASE)
        cond_match  = re.search(
            r"\b(sunny|clear|cloudy|partly cloudy|overcast|rain|drizzle|thunderstorm|foggy|haze|windy|humid|showers|snow)\b",
            combined, re.IGNORECASE
        )

        if temp_match:
            temp   = temp_match.group(1)
            humid  = humid_match.group(1) + "%" if humid_match else "N/A"
            cond   = cond_match.group(1).title() if cond_match else "Check local forecast"
            return (
                f"Temperature : {temp}°C\n"
                f"Condition : {cond}"
            )

        # Last resort: return first two clean sentences from snippet
        sentences = re.split(r"(?<=[.!?])\s+", combined)
        good = [s.strip() for s in sentences if 15 < len(s.strip()) < 200]
        return " ".join(good[:2]) or "Weather data unavailable."

    except Exception as e:
        return f"Weather lookup failed: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# Agent entry point
# ──────────────────────────────────────────────────────────────────────────────

def weather_agent(state: dict) -> dict:
    """
    Fetch current weather + 3-day forecast for state["destination"].
    Tries WeatherAPI first; falls back to Tavily search.
    Writes: weather (formatted string)
    """
    destination = state.get("destination", "")

    if not destination or destination == "Unknown":
        return {"weather": "Weather lookup skipped: destination unknown."}

    current_weather = _fetch_from_weatherapi(destination)

    if current_weather is None:  # key missing or API error → use Tavily
        weather = _fetch_from_tavily(destination)
    else:
        # Try to get 3-day forecast
        forecast = _fetch_forecast_from_weatherapi(destination)
        if forecast:
            weather = (
                current_weather
                + "\n\n  📆 3-Day Forecast\n"
                + forecast
            )
        else:
            weather = current_weather

    return {"weather": weather}