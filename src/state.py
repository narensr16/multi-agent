"""
state.py — Shared LangGraph state for the Travel Assistant.

Design rules:
  • Only supervisor writes: destination, days, budget
  • Each worker only writes its OWN key (weather / hotels / transport / estimated_cost)
  • final_response is written once by supervisor_final
  • messages is Annotated so every node can append without conflict
"""

from typing import Annotated, Any, List, Optional, TypedDict
import operator

class AgentState(TypedDict):
    # Initial input
    user_query: str

    # Parsed structured data
    destination: Optional[str]
    origin: Optional[str]
    days: Optional[str]
    budget: Optional[float]

    # Worker-agent outputs
    weather: Optional[str]
    hotels: Optional[list]
    hotel_price_raw: Optional[str]
    hotel_price_inr: Optional[float]
    transport: Optional[str]
    itinerary: Optional[str]
    flights: Optional[str]
    estimated_cost: Optional[dict]
    activities_cost: Optional[float]
    map_url: Optional[str]
    map_places: Optional[list]

    # Final assembled response
    final_response: Optional[str]

    # Conversation log
    messages: Annotated[List[Any], operator.add]