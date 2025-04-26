import streamlit as st
import os
import sys

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

from src.components.data_dashboard import display_data_dashboard

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
    
    st.write("""
    ### About This Platform
    
    This data-driven BTR investment platform helps identify top UK rental opportunities using free, open-source tools.
    The platform integrates data from multiple sources to provide comprehensive insights for BTR investments.
    
    ### Key Features:
    
    - **Data Integration**: Combines data from Land Registry, ONS, Planning Portal, OpenStreetMap, and EPC ratings
    - **Location Analysis**: Scores locations based on multiple factors including amenities and rental potential
    - **Investment Calculator**: Calculates potential returns including purchase costs, refurbishment, and rental yield
    - **Risk Assessment**: Evaluates investment risks based on market data and property characteristics
    
    ### Getting Started
    
    Use the navigation menu on the left to explore different sections of the platform:
    
    1. **Data Explorer**: Browse and analyze the integrated property data
    2. **Investment Calculator**: Calculate potential returns on BTR investments
    
    ### Data Sources
    
    This platform integrates data from the following sources:
    
    - **Land Registry Price Data**: Historical property transaction data
    - **ONS Rental Statistics**: Official rental price statistics
    - **Planning Portal Applications**: Local planning applications
    - **OpenStreetMap Amenities**: Location-based amenities such as schools, transport, and shops
    - **EPC Energy Ratings**: Energy efficiency ratings for properties
    """)
    
    # Check if data has been collected
    data_files = os.listdir('data/processed') if os.path.exists('data/processed') else []
    if not data_files:
        st.warning("No data has been collected yet. Please run the data collection script first.")
        st.info("You can run the data collection with: `python scripts/run_data_collection.py --run-now`")
    else:
        st.success(f"Data collection is set up. Found {len(data_files)} processed data files.")
    
elif page == "Data Explorer":
    display_data_dashboard()
    
elif page == "Investment Calculator":
    st.write("## Investment Calculator")
    st.write("The Investment Calculator will be available in Week 2 of the project.")
    st.info("Check back soon for the ability to calculate potential returns on BTR investments.")