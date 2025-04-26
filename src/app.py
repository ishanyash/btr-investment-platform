import streamlit as st

st.set_page_config(
    page_title="BTR Investment Platform",
    page_icon="🏘️",
    layout="wide"
)

st.title("UK BTR Investment Platform")
st.write("""
This platform analyzes Buy-to-Rent investment opportunities across the UK using
multiple data sources to help identify high-performing areas and properties.
""")

# Add sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a page",
    ["Home", "Data Explorer", "Investment Calculator"]
)

# Simple routing
if page == "Home":
    st.write("## Welcome to the BTR Investment Platform")
    st.write("Use the sidebar to navigate through the platform's features.")
elif page == "Data Explorer":
    st.write("## Data Explorer")
    st.write("Here you'll be able to explore property data from various sources.")
elif page == "Investment Calculator":
    st.write("## Investment Calculator")
    st.write("Calculate potential returns on BTR investments.")