import pandas as pd
import json
import folium
import streamlit as st
from folium.plugins import HeatMap, MarkerCluster
import os
import sys

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(project_root)

from src.utils.data_processor import load_amenities_data, load_land_registry_data, postcode_to_area

def display_btr_map():
    """Display the BTR hotspot map in Streamlit"""
    st.title("UK BTR Investment Hotspots")
    
    # Map type selection
    map_type = st.radio(
        "Select map type:",
        ["Markers", "Heatmap", "Both"],
        horizontal=True,
        index=0
    )
    
    # Create a map centered on the UK
    uk_center = [54.7, -4.2]
    uk_zoom = 6
    
    # Load data for the map
    amenities_data = load_amenities_data()
    land_registry_data = load_land_registry_data()
    
    # Create base map
    m = folium.Map(location=uk_center, zoom_start=uk_zoom, 
                  tiles='CartoDB Positron')
    
    # Add title
    title_html = """
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index: 9999; 
                background-color: white; padding: 10px; border-radius: 5px; border: 2px solid #73AD21;">
        <h3 style="margin: 0;">UK BTR Investment Hotspots</h3>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Get BTR hotspot data
    hotspots = get_btr_hotspots(amenities_data, land_registry_data)
    
    if map_type.lower() in ['markers', 'both']:
        # Create marker cluster
        marker_cluster = MarkerCluster().add_to(m)
        
        # Add markers for each hotspot
        for spot in hotspots:
            # Create popup content
            popup_content = f"""
            <div style="width: 200px;">
                <h4>{spot['location']}</h4>
                <p><strong>BTR Score:</strong> {spot['score']}/100</p>
            """
            
            # Add component scores if available
            if 'component_scores' in spot:
                popup_content += "<ul>"
                for component, score in spot['component_scores'].items():
                    if component != 'base':
                        popup_content += f"<li>{component.title()}: {score:.1f}</li>"
                popup_content += "</ul>"
            
            popup_content += "</div>"
            
            # Create marker
            folium.Marker(
                location=[spot['lat'], spot['lon']],
                popup=folium.Popup(popup_content, max_width=250),
                tooltip=f"{spot['location']} - Score: {spot['score']}",
                icon=folium.Icon(color='white', icon_color=spot['color'], icon='home', prefix='fa')
            ).add_to(marker_cluster)
    
    if map_type.lower() in ['heatmap', 'both']:
        # Create data for heatmap
        heat_data = [[spot['lat'], spot['lon'], spot['score']/100] for spot in hotspots]
        
        # Add heatmap layer
        HeatMap(heat_data, radius=25, gradient={
            0.2: 'blue',
            0.4: 'lime',
            0.6: 'yellow',
            0.8: 'orange',
            1.0: 'red'
        }).add_to(m)
    
    # Add legend
    color_scale = {
        'excellent': '#1a9850',  # Green (80-100)
        'good': '#91cf60',       # Light Green (70-80)
        'above_average': '#d9ef8b', # Yellow-Green (60-70)
        'average': '#ffffbf',    # Yellow (50-60)
        'below_average': '#fee08b', # Light Orange (40-50)
        'poor': '#fc8d59',       # Orange (30-40)
        'very_poor': '#d73027'   # Red (0-30)
    }
    
    legend_html = """
    <div style="position: fixed; bottom: 50px; right: 50px; z-index: 9999; background-color: white; 
                padding: 10px; border-radius: 5px; border: 2px solid #73AD21;">
        <h4 style="margin-top: 0;">BTR Score Legend</h4>
    """
    
    for label, color in color_scale.items():
        legend_html += f"""
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 20px; height: 20px; background-color: {color}; margin-right: 5px;"></div>
            <div>{label.replace('_', ' ').title()}</div>
        </div>
        """
    
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Display map in Streamlit
    st.components.v1.html(m._repr_html_(), height=600)
    
    # Add download button for the map
    map_html_str = m.get_root().render()
    st.download_button(
        "Download Map",
        map_html_str,
        file_name="btr_hotspot_map.html",
        mime="text/html"
    )
    
    # Show top locations table
    st.subheader("Top BTR Investment Locations")
    sorted_hotspots = sorted(hotspots, key=lambda x: x['score'], reverse=True)
    top_locations = sorted_hotspots[:10]
    
    # Create DataFrame
    top_df = pd.DataFrame([{
        'Location': spot['location'],
        'BTR Score': spot['score'],
        'Category': get_score_category(spot['score'])
    } for spot in top_locations])
    
    st.table(top_df)


def get_score_category(score):
    """Get category based on score range"""
    if score >= 80:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 60:
        return "Above Average"
    elif score >= 50:
        return "Average"
    elif score >= 40:
        return "Below Average"
    elif score >= 30:
        return "Poor"
    else:
        return "Very Poor"


def get_score_color(score):
    """Get color based on score range"""
    color_scale = {
        'excellent': '#1a9850',  # Green (80-100)
        'good': '#91cf60',       # Light Green (70-80)
        'above_average': '#d9ef8b', # Yellow-Green (60-70)
        'average': '#ffffbf',    # Yellow (50-60)
        'below_average': '#fee08b', # Light Orange (40-50)
        'poor': '#fc8d59',       # Orange (30-40)
        'very_poor': '#d73027'   # Red (0-30)
    }
    
    if score >= 80:
        return color_scale['excellent']
    elif score >= 70:
        return color_scale['good']
    elif score >= 60:
        return color_scale['above_average']
    elif score >= 50:
        return color_scale['average']
    elif score >= 40:
        return color_scale['below_average']
    elif score >= 30:
        return color_scale['poor']
    else:
        return color_scale['very_poor']


def get_btr_hotspots(amenities_data=None, land_registry_data=None):
    """Get BTR hotspot data for the map"""
    # Major UK cities coordinates and default scores
    major_cities = {
        'London': {'lat': 51.5074, 'lon': -0.1278, 'score': 85},
        'Manchester': {'lat': 53.4808, 'lon': -2.2426, 'score': 82},
        'Birmingham': {'lat': 52.4862, 'lon': -1.8904, 'score': 78},
        'Leeds': {'lat': 53.8008, 'lon': -1.5491, 'score': 76},
        'Glasgow': {'lat': 55.8642, 'lon': -4.2518, 'score': 72},
        'Liverpool': {'lat': 53.4084, 'lon': -2.9916, 'score': 74},
        'Bristol': {'lat': 51.4545, 'lon': -2.5879, 'score': 77},
        'Sheffield': {'lat': 53.3811, 'lon': -1.4701, 'score': 70},
        'Edinburgh': {'lat': 55.9533, 'lon': -3.1883, 'score': 75},
        'Cardiff': {'lat': 51.4816, 'lon': -3.1791, 'score': 71},
        'Belfast': {'lat': 54.5973, 'lon': -5.9301, 'score': 68},
        'Nottingham': {'lat': 52.9548, 'lon': -1.1581, 'score': 73},
        'Newcastle': {'lat': 54.9783, 'lon': -1.6178, 'score': 69}
    }
    
    # Create hotspots list
    hotspots = []
    
    # Add major cities with default scores
    for city, data in major_cities.items():
        # Add component scores based on Knight Frank reports
        component_scores = {
            'base': 50,
            'amenities': min(data['score'] / 5, 20),  # Scale to 0-20
            'rental': min(data['score'] / 4, 25),     # Scale to 0-25
            'property_value': min(data['score'] / 5, 20),  # Scale to 0-20
            'growth': min(data['score'] / 5, 20),     # Scale to 0-20
            'efficiency': min(data['score'] / 7, 15)  # Scale to 0-15
        }
        
        hotspots.append({
            'location': city,
            'lat': data['lat'],
            'lon': data['lon'],
            'score': data['score'],
            'color': get_score_color(data['score']),
            'component_scores': component_scores,
            'data_quality': 'estimated'
        })
    
    # If we have amenities data, add those locations
    if amenities_data is not None and 'location' in amenities_data.columns:
        unique_locations = amenities_data['location'].unique()
        
        for location in unique_locations:
            # Skip if already in major cities
            if location in major_cities:
                continue
                
            # Get location data
            location_data = amenities_data[amenities_data['location'] == location]
            
            if 'lat' in location_data.columns and 'lon' in location_data.columns:
                lat = location_data['lat'].mean()
                lon = location_data['lon'].mean()
                
                # Calculate score based on amenities
                score = 50  # Base score
                
                if 'amenity_score' in location_data.columns:
                    amenity_score = location_data['amenity_score'].mean()
                    score += min(amenity_score / 4, 25)  # Max 25 points from amenities
                
                # Add to hotspots
                hotspots.append({
                    'location': location,
                    'lat': lat,
                    'lon': lon,
                    'score': int(score),
                    'color': get_score_color(score),
                    'data_quality': 'calculated'
                })
    
    return hotspots