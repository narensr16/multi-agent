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

    # Worker-agent outputs (each agent writes exactly one of these)
    weather: Optional[str]
    hotels: Optional[str]
    transport: Optional[str]
    itinerary: Optional[str]
    flights: Optional[str]
    estimated_cost: Optional[str]

    # Final assembled response (written ONLY by supervisor_final)
    final_response: Optional[str]

    # Conversation log — uses Annotated so multiple nodes can append safely
    messages: Annotated[List[Any], operator.add]