import streamlit as st
import os
import sys
import pandas as pd
import plotly.express as px

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

# Import components
from src.components.data_dashboard import display_data_dashboard
from src.components.investment_calculator_page import display_investment_calculator
from src.components.mapping_util import display_btr_map
from src.components.recommendations_page import display_recommendations

st.set_page_config(
    page_title="BTR Investment Platform",
    page_icon="🏘️",
    layout="wide"
)

def main():
    st.title("UK BTR Investment Platform")
    
    # Add sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select a page",
        ["Home", "BTR Hotspot Map", "Investment Calculator", "Recommendations", "Data Explorer"]
    )
    
    # Simple routing
    if page == "Home":
        display_home()
    elif page == "BTR Hotspot Map":
        display_btr_map()
    elif page == "Investment Calculator":
        display_investment_calculator()
    elif page == "Recommendations":
        display_recommendations()
    elif page == "Data Explorer":
        display_data_dashboard()


def display_home():
    """Display the home page"""
    st.write("## Welcome to the BTR Investment Platform")
    
    # Display key metrics from Knight Frank reports
    st.write("### BTR Market Overview")
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="BTR Investment in 2024",
            value="£5.2B",
            delta="+11%",
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            label="SFH Investment Share",
            value="36%",
            delta="+5%",
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            label="Completed BTR Homes",
            value="126,000",
            delta="+21%",
            delta_color="normal"
        )
    
    with col4:
        st.metric(
            label="Average Resident Experience Premium",
            value="14%",
            help="Premium commanded by properties with high resident experience ratings"
        )
    
    # About section
    st.write("""
    ### About This Platform
    
    This data-driven BTR investment platform helps identify top UK rental opportunities using free, open-source tools.
    The platform integrates data from multiple sources to provide comprehensive insights for BTR investments.
    
    ### Key Features:
    
    - **Location Scoring Algorithm**: Rates UK locations on a 0-100 scale based on BTR investment potential
    - **Investment Calculator**: Calculates potential returns including purchase costs, refurbishment, and rental yield
    - **Interactive Map**: Visualizes BTR hotspots across the UK
    - **Data Integration**: Combines data from Land Registry, ONS, Planning Portal, OpenStreetMap, and EPC ratings
    """)
    
    # Show key insights from Knight Frank reports
    st.write("### Key BTR Market Insights")
    
    # Create tabs for different insights
    tab1, tab2, tab3 = st.tabs(["Market Trends", "Resident Experience", "Regional Outlook"])
    
    with tab1:
        st.write("""
        - Investment in UK Build to Rent (BTR) surpassed £5 billion for the first time in 2024
        - Single Family Housing (SFH) accounted for 36% of total BTR investment in 2024
        - Funding new development remains the primary route to market, accounting for 70% of deals
        - Banks are now more willing to offer up to 60% loan-to-value for BTR projects
        """)
        
        # Create sample chart for investment trends
        years = [2020, 2021, 2022, 2023, 2024]
        investment = [3.1, 3.5, 4.3, 4.7, 5.2]
        
        fig = px.line(
            x=years, y=investment,
            labels={"x": "Year", "y": "Investment (£ Billion)"},
            title="UK BTR Investment Growth"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.write("""
        - Schemes with the highest Resident Experience scores can command a 14% rental premium
        - The average Band A-rated scheme has six community-focused services
        - Larger unit sizes (63 sqm on average) support better resident experience
        - Better energy efficiency correlates with higher resident satisfaction
        - Energy costs average £5.29 per sqm in top-rated schemes vs. £11.52 in lowest-rated schemes
        """)
        
        # Create sample chart for resident experience impact
        categories = ["Band A", "Band B", "Band C", "Band D", "Band E"]
        rental_premium = [14, 8, 3, -1, -2]
        
        fig = px.bar(
            x=categories, y=rental_premium,
            labels={"x": "Resident Experience Band", "y": "Rental Premium vs. Local Market (%)"},
            title="Impact of Resident Experience on Rental Premiums"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.write("""
        - 68% of BTR completions in 2024 were outside of London
        - The North West accounted for 16% of completions, followed by the South East and West Midlands
        - Scotland accounted for 10% of delivery in 2024 but only 4% of the future pipeline
        - Manchester, Birmingham and Leeds remain key regional BTR markets
        - The imbalance between supply and demand continues to underpin rental growth
        """)
        
        # Create sample chart for regional distribution
        regions = ["London", "North West", "South East", "West Midlands", "Scotland", "Other Regions"]
        completions = [32, 16, 14, 12, 10, 16]
        
        fig = px.pie(
            values=completions, names=regions,
            title="Regional Distribution of BTR Completions (2024)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Getting Started section
    st.write("""
    ### Getting Started
    
    Use the navigation menu on the left to explore different sections of the platform:
    
    1. **BTR Hotspot Map**: Explore the interactive map of BTR investment hotspots across the UK
    2. **Investment Calculator**: Calculate potential returns on BTR investments with detailed analysis
    3. **Data Explorer**: Browse and analyze the integrated property data
    """)
    
    # Check if data has been collected
    data_files = os.listdir('data/processed') if os.path.exists('data/processed') else []
    if not data_files:
        st.warning("No data has been collected yet. Please run the data collection script first.")
        st.info("You can run the data collection with: `python scripts/run_data_collection.py --run-now`")
    else:
        st.success(f"Data collection is set up. Found {len(data_files)} processed data files.")


if __name__ == "__main__":
    main()