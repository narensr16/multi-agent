import streamlit as st
import os
# Triggering redeploy - v2.3 - Final Refinements
import sys
import re

# Ensure the 'src' directory is in the import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()

from graph import build_graph

# Configure the page
st.set_page_config(
    page_title="AI Travel Assistant",
    page_icon="🌍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.title("🌍 AI Travel Assistant")
st.markdown("Powered by **LangGraph** & **Tavily Search** | `v2.4 - Final Refined`")
st.markdown("---")

# Initialize graph securely in session state
if "app" not in st.session_state:
    st.session_state.app = build_graph()

# Input area
with st.form("travel_form"):
    user_query = st.text_input(
        "Where do you want to go?",
        placeholder="e.g. Plan a 5-day trip to Goa from Delhi with 50000 budget",
        help="Include your origin, destination, days, and budget for the best results."
    )
    submit = st.form_submit_button("Generate Travel Plan 🚀")

st.markdown("---")


def _render_plan(plan: str):
    """Render the travel plan intelligently — map links are clickable HTML."""
    # Split on the MAP section header
    map_sep = "🗺  MAP"
    cost_sep = "💰  ESTIMATED COST"

    before_map, _, rest = plan.partition(map_sep)

    # Display everything before the MAP section
    st.text(before_map)

    if rest:
        # Display MAP section header
        st.markdown("### 🗺  MAP")
        st.markdown("---")

        # Split off the cost section that comes after MAP
        map_part, _, after_map = rest.partition(cost_sep)

        # Convert raw URLs in the map block to clickable markdown links
        def _linkify(line: str) -> str:
            # Replace "name → https://url" with "name → [maps](url)"
            m = re.match(r"(\s*[∙•]\s*)(.*?)\s*→\s*(https?://\S+)", line)
            if m:
                prefix, name, url = m.group(1), m.group(2), m.group(3)
                return f"{prefix}**{name}** → [Open in Maps 📍]({url})"
            # Replace plain "🔗 View on Google Maps: https://..." line
            m2 = re.match(r"(\s*🔗.*?:\s*)(https?://\S+)", line)
            if m2:
                label, url = m2.group(1), m2.group(2)
                return f"{label}[**Click to Open Maps 🗺**]({url})"
            return line

        map_lines = map_part.split("\n")
        rendered = "\n".join(_linkify(l) for l in map_lines)
        st.markdown(rendered)
        st.markdown("---")

        # Display the rest (cost section onwards)
        if after_map:
            st.text(cost_sep + after_map)
    else:
        # No map section — just display everything
        st.text(plan)


if submit and user_query:
    st.info("⏳ Planning your trip... This may take up to 30 seconds.")

    initial_state = {
        "user_query": user_query,
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
        "map_url":     None,
        "map_places":  None,
        "final_response": None,
    }

    try:
        # Run the workflow
        final_state = st.session_state.app.invoke(initial_state)
        plan = final_state.get("final_response", "")

        if plan:
            st.success("✅ Your AI-generated travel plan is ready!")
            _render_plan(plan)

            # Allow downloading
            dest = final_state.get("destination", "Unknown").replace(" ", "_")
            st.download_button(
                label="📥 Download Plan (.txt)",
                data=plan,
                file_name=f"travel_plan_{dest}.txt",
                mime="text/plain"
            )
        else:
            st.error("⚠️ Could not generate a complete plan. Please try modifying your request.")

    except Exception as e:
        st.error(f"❌ An error occurred during planning: {str(e)}")
        st.write("Please check your API keys and try again.")

# Sidebar instructions
with st.sidebar:
    st.markdown("### About")
    st.markdown(
        "This AI Agent uses:\n"
        "- **LangGraph** for multi-agent reasoning\n"
        "- **Tavily** for live web searches (hotels, attractions)\n"
        "- **Groq Llama-3** for intelligent LLM parsing\n"
        "- **Amadeus** for actual flight prices\n"
        "- **WeatherAPI** for live forecasts & 3-day outlook\n"
        "- **Google Maps** links for all attractions"
    )
