import streamlit as st

from interface.uis import chatbot, control_panel, dashboard

available_uis = {
    "Chatbot 🤖": chatbot.ui,
    "Control Panel 🎚️": control_panel.ui,
    "Dashboard 📊": dashboard.ui,
}

with st.sidebar:
    chosen_ui = st.selectbox("Choose UI", available_uis.keys())

available_uis[chosen_ui]()
