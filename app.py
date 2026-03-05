import streamlit as st
import os
import sys

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
st.markdown("Powered by **LangGraph** & **Tavily Search**")
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
        "final_response": None,
    }

    try:
        # Run the workflow
        final_state = st.session_state.app.invoke(initial_state)
        plan = final_state.get("final_response", "")
        
        if plan:
            # Display successful plan visually
            st.success("✅ Your AI-generated travel plan is ready!")
            st.text_area("Your Travel Plan", value=plan, height=800, label_visibility="collapsed")
            
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
        "- **Amadeus** for actual flight prices\n"
        "- **WeatherAPI** for local forecasts"
    )
