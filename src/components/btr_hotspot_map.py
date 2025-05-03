import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MarkerCluster
import streamlit as st
import json
import os
from .location_score_algorithm import calculate_location_score

class BTRHotspotMap:
    """
    Interactive UK map showing BTR investment hotspots
    """
    
    def __init__(self, land_registry_data=None, rental_data=None, 
                 amenities_data=None, epc_data=None, planning_data=None):
        """Initialize with available data"""
        self.land_registry_data = land_registry_data
        self.rental_data = rental_data
        self.amenities_data = amenities_data
        self.epc_data = epc_data
        self.planning_data = planning_data
        
        # Default UK coordinates
        self.uk_center = [54.7, -4.2]
        self.uk_zoom = 6
        
        # Major UK cities coordinates
        self.major_cities = {
            'London': {'lat': 51.5074, 'lon': -0.1278},
            'Manchester': {'lat': 53.4808, 'lon': -2.2426},
            'Birmingham': {'lat': 52.4862, 'lon': -1.8904},
            'Leeds': {'lat': 53.8008, 'lon': -1.5491},
            'Glasgow': {'lat': 55.8642, 'lon': -4.2518},
            'Liverpool': {'lat': 53.4084, 'lon': -2.9916},
            'Bristol': {'lat': 51.4545, 'lon': -2.5879},
            'Sheffield': {'lat': 53.3811, 'lon': -1.4701},
            'Edinburgh': {'lat': 55.9533, 'lon': -3.1883},
            'Cardiff': {'lat': 51.4816, 'lon': -3.1791},
            'Belfast': {'lat': 54.5973, 'lon': -5.9301},
            'Nottingham': {'lat': 52.9548, 'lon': -1.1581},
            'Newcastle': {'lat': 54.9783, 'lon': -1.6178}
        }
        
        # Color mapping for scores
        self.color_scale = {
            'excellent': '#1a9850',  # Green (80-100)
            'good': '#91cf60',       # Light Green (70-80)
            'above_average': '#d9ef8b', # Yellow-Green (60-70)
            'average': '#ffffbf',    # Yellow (50-60)
            'below_average': '#fee08b', # Light Orange (40-50)
            'poor': '#fc8d59',       # Orange (30-40)
            'very_poor': '#d73027'   # Red (0-30)
        }
    
    def _get_score_color(self, score):
        """Get color based on score range"""
        if score >= 80:
            return self.color_scale['excellent']
        elif score >= 70:
            return self.color_scale['good']
        elif score >= 60:
            return self.color_scale['above_average']
        elif score >= 50:
            return self.color_scale['average']
        elif score >= 40:
            return self.color_scale['below_average']
        elif score >= 30:
            return self.color_scale['poor']
        else:
            return self.color_scale['very_poor']
    
    def _calculate_hotspot_scores(self):
        """Calculate BTR hotspot scores for locations"""
        hotspots = []
        
        # Start with major cities as a fallback
        for city, location in self.major_cities.items():
            # Default score based on market knowledge (to be improved with data)
            score = self._get_default_city_score(city)
            
            # Append with default data
            hotspots.append({
                'location': city,
                'lat': location['lat'],
                'lon': location['lon'],
                'score': score,
                'color': self._get_score_color(score),
                'data_quality': 'estimated'
            })
        
        # If we have actual data, use it to calculate scores
        if any([self.land_registry_data is not None, 
                self.rental_data is not None,
                self.amenities_data is not None,
                self.epc_data is not None]):
            
            # Get locations from data
            locations = self._extract_locations_from_data()
            
            # Calculate scores for each location
            for location in locations:
                try:
                    score_result = calculate_location_score(
                        location,
                        amenities_data=self.amenities_data,
                        rental_data=self.rental_data,
                        epc_data=self.epc_data,
                        land_registry_data=self.land_registry_data,
                        planning_data=self.planning_data
                    )
                    
                    # Get coordinates (this would need to be adapted based on your data)
                    coords = self._get_location_coordinates(location)
                    
                    if coords:
                        hotspots.append({
                            'location': location,
                            'lat': coords['lat'],
                            'lon': coords['lon'],
                            'score': score_result['overall_score'],
                            'component_scores': score_result['component_scores'],
                            'color': self._get_score_color(score_result['overall_score']),
                            'data_quality': 'calculated'
                        })
                except Exception as e:
                    print(f"Error calculating score for {location}: {e}")
        
        return hotspots
    
    def _extract_locations_from_data(self):
        """Extract unique locations from the data"""
        locations = set()
        
        # Extract from amenities data
        if self.amenities_data is not None and 'location' in self.amenities_data.columns:
            locations.update(self.amenities_data['location'].unique())
        
        # Extract from rental data (if it has location/region)
        if self.rental_data is not None and 'region' in self.rental_data.columns:
            locations.update(self.rental_data['region'].unique())
        
        # Extract from land registry (postcode districts)
        if self.land_registry_data is not None and 'postcode' in self.land_registry_data.columns:
            # Extract postcode districts (first half of postcode)
            districts = self.land_registry_data['postcode'].apply(
                lambda x: x.split(' ')[0] if isinstance(x, str) and ' ' in x else x
            )
            locations.update(districts.unique())
        
        return locations
    
    def _get_location_coordinates(self, location):
        """Get coordinates for a location"""
        # First check if it's a major city
        for city, coords in self.major_cities.items():
            if location.lower() == city.lower():
                return coords
        
        # Check if it's in amenities data
        if self.amenities_data is not None and 'location' in self.amenities_data.columns:
            location_data = self.amenities_data[self.amenities_data['location'] == location]
            if not location_data.empty and 'lat' in location_data.columns and 'lon' in location_data.columns:
                lat = location_data['lat'].mean()
                lon = location_data['lon'].mean()
                return {'lat': lat, 'lon': lon}
        
        # For postcode districts, would need a lookup table or geocoding service
        # This is a simplified approach
        return None
    
    def _get_default_city_score(self, city):
        """Get default BTR score for major cities based on market knowledge"""
        # These scores are based on Knight Frank reports and market knowledge
        # Would be refined with actual data
        city_scores = {
            'London': 85,
            'Manchester': 82,
            'Birmingham': 78,
            'Leeds': 76,
            'Glasgow': 72,
            'Liverpool': 74,
            'Bristol': 77,
            'Sheffield': 70,
            'Edinburgh': 75,
            'Cardiff': 71,
            'Belfast': 68,
            'Nottingham': 73,
            'Newcastle': 69
        }
        
        return city_scores.get(city, 50)  # Default 50 if not in list
    
    def create_map(self, map_type='markers'):
        """
        Create an interactive map of BTR hotspots
        
        Parameters:
        -----------
        map_type : str
            Type of map to create ('markers', 'heatmap', or 'both')
            
        Returns:
        --------
        folium.Map
            Interactive map object
        """
        # Calculate hotspot scores
        hotspots = self._calculate_hotspot_scores()
        
        # Create base map
        m = folium.Map(location=self.uk_center, zoom_start=self.uk_zoom, 
                      tiles='CartoDB Positron')
        
        # Add title
        title_html = """
        <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index: 9999; 
                    background-color: white; padding: 10px; border-radius: 5px; border: 2px solid #73AD21;">
            <h3 style="margin: 0;">UK BTR Investment Hotspots</h3>
        </div>
        """
        m.get_root().html.add_child(folium.Element(title_html))
        
        if map_type in ['markers', 'both']:
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
        
        if map_type in ['heatmap', 'both']:
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
        legend_html = """
        <div style="position: fixed; bottom: 50px; right: 50px; z-index: 9999; background-color: white; 
                    padding: 10px; border-radius: 5px; border: 2px solid #73AD21;">
            <h4 style="margin-top: 0;">BTR Score Legend</h4>
        """
        
        for label, color in self.color_scale.items():
            legend_html += f"""
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="width: 20px; height: 20px; background-color: {color}; margin-right: 5px;"></div>
                <div>{label.replace('_', ' ').title()}</div>
            </div>
            """
        
        legend_html += "</div>"
        m.get_root().html.add_child(folium.Element(legend_html))
        
        return m
    
    def display_streamlit_map(self):
        """Display interactive map in Streamlit"""
        st.subheader("UK BTR Investment Hotspot Map")
        
        # Map type selection
        map_type = st.radio(
            "Select map type:",
            ["Markers", "Heatmap", "Both"],
            horizontal=True,
            index=0
        )
        
        # Create map
        m = self.create_map(map_type.lower())
        
        # Convert to HTML and display in Streamlit
        map_html = m._repr_html_()
        st.components.v1.html(map_html, height=600)
        
        # Add download button for the map
        map_html_str = m.get_root().render()
        st.download_button(
            "Download Map",
            map_html_str,
            file_name="btr_hotspot_map.html",
            mime="text/html"
        )
        
        return m
    
    def get_top_locations(self, n=10):
        """Get top n BTR investment locations"""
        hotspots = self._calculate_hotspot_scores()
        
        # Sort by score (descending)
        sorted_hotspots = sorted(hotspots, key=lambda x: x['score'], reverse=True)
        
        # Return top n
        return sorted_hotspots[:n]


def create_sample_map():
    """Create sample map with default data"""
    hotspot_map = BTRHotspotMap()
    return hotspot_map.create_map()


if __name__ == "__main__":
    # Example usage
    map_obj = create_sample_map()
    map_obj.save('btr_hotspot_map.html')