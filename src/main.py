"""
main.py — Entry point for the AI Travel Assistant

Usage:
    python src/main.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()  # load TAVILY_API_KEY and OPENAI_API_KEY from .env

from graph import build_graph

BANNER = """
╔══════════════════════════════════════════════════════╗
║        🌏  AI TRAVEL ASSISTANT  (LangGraph)          ║
║           Powered by Tavily Internet Search          ║
╚══════════════════════════════════════════════════════╝
"""

EXAMPLES = [
    "I want to visit Kodaikanal for 3 days with 30000 budget",
    "Plan a 5-day trip to Goa with a budget of 50000",
    "I want to go to Manali for 7 days with 45000 budget",
]


def main() -> None:
    print(BANNER)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=str)
    parser.add_argument("--origin", type=str)
    parser.add_argument("--days", type=int)
    parser.add_argument("--budget", type=int)
    args, _ = parser.parse_known_args()

    if args.destination and args.days and args.budget:
        origin_part = f" from {args.origin}" if args.origin else ""
        user_input = f"I want to visit {args.destination}{origin_part} for {args.days} days with {args.budget} budget"
    else:
        print("📌 Example queries:")
        for q in EXAMPLES:
            print(f"   → {q}")
        print()

        user_input = input("Enter your travel request: ").strip()
        
    if not user_input:
        print("No input provided. Exiting.")
        sys.exit(0)

    print("\n⏳ Planning your trip… (this may take a few seconds)\n")

    # Build the compiled LangGraph
    app = build_graph()

    # Initial state — note: no **state spreading from nodes, so we keep
    # fields minimal here and let the supervisor fill the rest.
    initial_state = {
        "user_query": user_input,
        "messages":   [],
        "destination": None,
        "origin":      None,
        "days":        None,
        "budget":      None,
        "weather":     None,
        "hotels":      None,
        "transport":   None,
        "itinerary":   None,
        "flights":     None,
        "estimated_cost": None,
        "final_response": None,
    }

    # Run the graph
    final_state = app.invoke(initial_state)

    # Print the assembled travel plan
    plan = final_state.get("final_response", "")
    dest = final_state.get('destination', 'Unknown').replace(" ", "_")
    
    if plan:
        print(plan)
        # Try to save to file
        try:
            filename = f"travel_plan_{dest}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(plan)
            print(f"✅ Plan successfully saved to {filename}")
        except Exception as e:
            print(f"⚠️ Could not save plan to file: {e}")
    else:
        # Fallback: print individual fields
        print("=" * 56)
        print("               🌍  AI TRAVEL PLAN")
        print("=" * 56)
        print(f"  Destination     : {final_state.get('destination', 'N/A')}")
        print(f"  Duration        : {final_state.get('days', 'N/A')} day(s)")
        print(f"  Budget          : ₹{final_state.get('budget', 0):,}")
        print()
        print(f"  Weather:\n    {final_state.get('weather', 'N/A')}")
        print()
        print(f"  Hotels:\n    {final_state.get('hotels', 'N/A')}")
        print()
        print(f"  Transport:\n    {final_state.get('transport', 'N/A')}")
        print()
        print(f"  Estimated Cost:\n    {final_state.get('estimated_cost', 'N/A')}")
        print("=" * 56)


if __name__ == "__main__":
    main()
