"""
graph.py — LangGraph StateGraph for the Travel Assistant

Sequential topology:

  supervisor_init   ← extracts destination / days / budget
       │
  weather_agent     ← writes "weather"
       │
  hotel_agent       ← writes "hotels"
       │
  transport_agent   ← writes "transport"
       │
  flight_agent      ← writes "flights"  (Amadeus live data)
       │
  itinerary_agent   ← writes "itinerary"
       │
  budget_agent      ← writes "estimated_cost"
       │
  supervisor_final  ← assembles "final_response"
       │
      END
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from langgraph.graph import StateGraph, END
from state import AgentState
from agents.supervisor  import supervisor_init, supervisor_final
from agents.weather     import weather_agent
from agents.hotel       import hotel_agent
from agents.transport   import transport_agent
from agents.flight      import flight_agent
from agents.itinerary   import itinerary_agent
from agents.budget      import budget_agent


def build_graph():
    """Build and compile the LangGraph StateGraph."""
    graph = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("supervisor_init",  supervisor_init)
    graph.add_node("weather_agent",    weather_agent)
    graph.add_node("hotel_agent",      hotel_agent)
    graph.add_node("transport_agent",  transport_agent)
    graph.add_node("flight_agent",     flight_agent)
    graph.add_node("itinerary_agent",  itinerary_agent)
    graph.add_node("budget_agent",     budget_agent)
    graph.add_node("supervisor_final", supervisor_final)

    # ── Sequential edges ──────────────────────────────────────────────────────
    graph.set_entry_point("supervisor_init")
    graph.add_edge("supervisor_init",  "weather_agent")
    graph.add_edge("weather_agent",    "hotel_agent")
    graph.add_edge("hotel_agent",      "transport_agent")
    graph.add_edge("transport_agent",  "flight_agent")
    graph.add_edge("flight_agent",     "itinerary_agent")
    graph.add_edge("itinerary_agent",  "budget_agent")
    graph.add_edge("budget_agent",     "supervisor_final")
    graph.add_edge("supervisor_final", END)

    return graph.compile()
