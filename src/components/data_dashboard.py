import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import sys

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(project_root)

from src.utils.data_processor import load_land_registry_data, load_ons_rental_data, load_planning_data, load_amenities_data, load_epc_data

def display_data_dashboard():
    st.header("BTR Data Explorer")
    
    # Sidebar for data selection
    st.sidebar.subheader("Data Sources")
    selected_source = st.sidebar.selectbox(
        "Select Data Source",
        ["Land Registry", "ONS Rentals", "Planning Applications", "Amenities", "EPC Ratings"]
    )
    
    # Load the selected data
    if selected_source == "Land Registry":
        data = load_land_registry_data()
        title = "Land Registry Property Sales"
        if data is not None:
            display_land_registry_data(data)
    
    elif selected_source == "ONS Rentals":
        data = load_ons_rental_data()
        title = "ONS Rental Statistics"
        if data is not None:
            display_ons_rental_data(data)
    
    elif selected_source == "Planning Applications":
        data = load_planning_data()
        title = "Planning Applications"
        if data is not None:
            display_planning_data(data)
    
    elif selected_source == "Amenities":
        data = load_amenities_data()
        title = "OpenStreetMap Amenities"
        if data is not None:
            display_amenities_data(data)
    
    elif selected_source == "EPC Ratings":
        data = load_epc_data()
        title = "EPC Energy Ratings"
        if data is not None:
            display_epc_data(data)
    
    # Show messages if data not available
    if data is None:
        st.warning(f"No {selected_source} data available yet. Please run the data collection script first.")
        st.info("You can run the data collection with: `python scripts/run_data_collection.py --run-now`")

def display_land_registry_data(data):
    st.subheader("Land Registry Property Sales")
    
    # Display basic statistics
    st.write(f"Total records: {len(data):,}")
    
    if 'price' in data.columns:
        avg_price = data['price'].mean()
        st.write(f"Average property price: £{avg_price:,.2f}")
    
    # Show property type distribution
    if 'property_type' in data.columns:
        st.subheader("Property Types")
        type_counts = data['property_type'].value_counts().reset_index()
        type_counts.columns = ['Property Type', 'Count']
        
        # Map property type codes if needed
        type_map = {
            'D': 'Detached',
            'S': 'Semi-detached',
            'T': 'Terraced',
            'F': 'Flat/Maisonette',
            'O': 'Other'
        }
        if type_counts['Property Type'].isin(type_map.keys()).all():
            type_counts['Property Type'] = type_counts['Property Type'].map(type_map)
        
        fig = px.pie(type_counts, names='Property Type', values='Count', title="Property Type Distribution")
        st.plotly_chart(fig)
    
    # Show price ranges
    if 'price' in data.columns:
        st.subheader("Price Distribution")
        fig = px.histogram(data, x='price', nbins=50, title="Property Price Distribution")
        fig.update_layout(xaxis_title="Price (£)", yaxis_title="Count")
        st.plotly_chart(fig)
    
    # Show data table with filters
    st.subheader("Data Explorer")
    st.dataframe(data.head(1000))

def display_ons_rental_data(data):
    st.subheader("ONS Rental Statistics")
    
    # Basic statistics
    st.write(f"Total records: {len(data):,}")
    
    # Show regional comparison if possible
    if 'region' in data.columns and 'value' in data.columns:
        # Get latest date for each region
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            latest_date = data['date'].max()
            latest_data = data[data['date'] == latest_date]
            
            st.subheader(f"Rental Prices by Region (as of {latest_date.strftime('%B %Y')})")
            
            fig = px.bar(latest_data, x='region', y='value', 
                         title=f"Rental Prices by Region (£/month)",
                         labels={'value': 'Average Rent (£/month)', 'region': 'Region'})
            st.plotly_chart(fig)
        
        # Show time series if multiple dates
        if 'date' in data.columns and len(data['date'].unique()) > 1:
            st.subheader("Rental Price Trends")
            
            # Group by region and date
            time_data = data.groupby(['region', 'date'])['value'].mean().reset_index()
            
            fig = px.line(time_data, x='date', y='value', color='region',
                          title="Rental Price Trends Over Time",
                          labels={'value': 'Average Rent (£/month)', 'date': 'Date', 'region': 'Region'})
            st.plotly_chart(fig)
    
    # Show data table
    st.subheader("Data Explorer")
    st.dataframe(data.head(1000))

def display_planning_data(data):
    st.subheader("Planning Applications")
    
    # Basic statistics
    st.write(f"Total records: {len(data):,}")
    
    # Show by status
    if 'status' in data.columns:
        status_counts = data['status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        st.subheader("Applications by Status")
        fig = px.pie(status_counts, names='Status', values='Count', title="Application Status Distribution")
        st.plotly_chart(fig)
    
    # Show by authority if available
    if 'authority' in data.columns:
        authority_counts = data['authority'].value_counts().reset_index()
        authority_counts.columns = ['Authority', 'Count']
        
        st.subheader("Applications by Local Authority")
        fig = px.bar(authority_counts, x='Authority', y='Count', title="Applications by Local Authority")
        st.plotly_chart(fig)
    
    # Show residential vs commercial if available
    if 'is_residential' in data.columns and 'is_commercial' in data.columns:
        st.subheader("Application Types")
        
        # Create summary
        types = {
            'Residential': data['is_residential'].sum(),
            'Commercial': data['is_commercial'].sum(),
            'Other': len(data) - data['is_residential'].sum() - data['is_commercial'].sum()
        }
        
        types_df = pd.DataFrame(list(types.items()), columns=['Type', 'Count'])
        fig = px.pie(types_df, names='Type', values='Count', title="Application Types")
        st.plotly_chart(fig)
    
    # Show data table
    st.subheader("Data Explorer")
    st.dataframe(data.head(1000))

def display_amenities_data(data):
    st.subheader("OpenStreetMap Amenities")
    
    # Basic statistics
    st.write(f"Total amenities: {len(data):,}")
    
    # Show by type
    if 'type' in data.columns:
        # Get top 15 amenity types
        type_counts = data['type'].value_counts().reset_index().head(15)
        type_counts.columns = ['Type', 'Count']
        
        st.subheader("Top Amenity Types")
        fig = px.bar(type_counts, x='Type', y='Count', title="Top 15 Amenity Types")
        st.plotly_chart(fig)
    
    # Show by location if available
    if 'location' in data.columns:
        location_counts = data['location'].value_counts().reset_index()
        location_counts.columns = ['Location', 'Count']
        
        st.subheader("Amenities by Location")
        fig = px.bar(location_counts, x='Location', y='Count', title="Amenities by Location")
        st.plotly_chart(fig)
    
    # Show data table
    st.subheader("Data Explorer")
    st.dataframe(data.head(1000))

def display_epc_data(data):
    st.subheader("EPC Energy Ratings")
    
    # Basic statistics
    st.write(f"Total records: {len(data):,}")
    
    # Show distribution of energy ratings
    if 'current_energy_rating' in data.columns:
        rating_counts = data['current_energy_rating'].value_counts().reset_index()
        rating_counts.columns = ['Rating', 'Count']
        
        # Sort by rating
        rating_order = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        rating_counts['Rating'] = pd.Categorical(rating_counts['Rating'], categories=rating_order, ordered=True)
        rating_counts = rating_counts.sort_values('Rating')
        
        st.subheader("EPC Rating Distribution")
        fig = px.bar(rating_counts, x='Rating', y='Count', title="EPC Rating Distribution",
                     color='Rating', color_discrete_map={
                         'A': 'green', 'B': 'lightgreen', 'C': 'yellow',
                         'D': 'orange', 'E': 'darkorange', 'F': 'red', 'G': 'darkred'
                     })
        st.plotly_chart(fig)
    
    # Show property types if available
    if 'property_type' in data.columns:
        type_counts = data['property_type'].value_counts().reset_index()
        type_counts.columns = ['Type', 'Count']
        
        st.subheader("Property Types")
        fig = px.pie(type_counts, names='Type', values='Count', title="Property Type Distribution")
        st.plotly_chart(fig)
    
    # Show improvement potential if available
    if 'efficiency_improvement' in data.columns:
        st.subheader("Energy Efficiency Improvement Potential")
        fig = px.histogram(data, x='efficiency_improvement', nbins=30,
                           title="Energy Efficiency Improvement Potential",
                           labels={'efficiency_improvement': 'Potential Improvement'})
        st.plotly_chart(fig)
    
    # Show data table
    st.subheader("Data Explorer")
    st.dataframe(data.head(1000))