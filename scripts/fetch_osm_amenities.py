import os
import pandas as pd
import requests
import json
from datetime import datetime

def fetch_osm_amenities(locations=None, output_dir='data/raw'):
    """
    Fetch amenity data from OpenStreetMap using Overpass API
    
    Args:
        locations: List of dictionaries with name, lat, lon and radius (meters)
        output_dir: Directory to save the output
    """
    if locations is None:
        # Default to some UK cities
        locations = [
            {"name": "Manchester", "lat": 53.4808, "lon": -2.2426, "radius": 2000},
            {"name": "Birmingham", "lat": 52.4862, "lon": -1.8904, "radius": 2000},
            {"name": "London-Center", "lat": 51.5074, "lon": -0.1278, "radius": 2000},
        ]
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Filename with date
    today = datetime.now().strftime('%Y%m%d')
    filename = f"{output_dir}/osm_amenities_{today}.json"
    
    all_amenities = []
    
    # Key amenity types for BTR assessment
    amenity_types = [
        "school", "restaurant", "cafe", "pub", "bar", "supermarket", 
        "hospital", "doctors", "pharmacy", "park", "cinema", "theatre",
        "gym", "fitness_centre", "public_transport", "subway_entrance"
    ]
    
    for location in locations:
        print(f"Fetching amenities for {location['name']}...")
        
        try:
            # Overpass API query for amenities
            overpass_url = "http://overpass-api.de/api/interpreter"
            
            # Build query for amenities within radius
            query = f"""
            [out:json];
            (
              node["amenity"](around:{location['radius']},{location['lat']},{location['lon']});
              node["leisure"](around:{location['radius']},{location['lat']},{location['lon']});
              node["shop"](around:{location['radius']},{location['lat']},{location['lon']});
              node["public_transport"](around:{location['radius']},{location['lat']},{location['lon']});
            );
            out body;
            """
            
            response = requests.post(overpass_url, data={"data": query})
            data = response.json()
            
            # Process results
            for element in data.get('elements', []):
                if element['type'] == 'node':
                    tags = element.get('tags', {})
                    
                    # Determine amenity type
                    amenity_type = None
                    if 'amenity' in tags:
                        amenity_type = tags['amenity']
                    elif 'leisure' in tags:
                        amenity_type = tags['leisure']
                    elif 'shop' in tags:
                        amenity_type = tags['shop']
                    elif 'public_transport' in tags:
                        amenity_type = tags['public_transport']
                    
                    if amenity_type:
                        all_amenities.append({
                            'location': location['name'],
                            'lat': element['lat'],
                            'lon': element['lon'],
                            'type': amenity_type,
                            'name': tags.get('name', 'Unknown'),
                            'osm_id': element['id']
                        })
            
        except Exception as e:
            print(f"Error fetching data for {location['name']}: {e}")
    
    if all_amenities:
        # Save as JSON
        with open(filename, 'w') as f:
            json.dump(all_amenities, f)
        
        # Also save as CSV for easier processing
        df = pd.DataFrame(all_amenities)
        csv_filename = filename.replace('.json', '.csv')
        df.to_csv(csv_filename, index=False)
        
        # Create processed version with amenity scores
        processed_filename = csv_filename.replace('raw', 'processed')
        
        # Group by location and count amenity types
        amenity_counts = df.groupby(['location', 'type']).size().unstack(fill_value=0)
        
        # Create amenity score (simple version)
        scores = pd.DataFrame()
        scores['location'] = amenity_counts.index
        scores['total_amenities'] = amenity_counts.sum(axis=1)
        
        # Calculate subscores
        # Food & dining
        food_cols = [col for col in amenity_counts.columns if col in ['restaurant', 'cafe', 'pub', 'bar']]
        scores['food_score'] = amenity_counts[food_cols].sum(axis=1) if food_cols else 0
        
        # Shopping
        shopping_cols = ['supermarket'] + [col for col in amenity_counts.columns if 'shop' in col]
        scores['shopping_score'] = amenity_counts[shopping_cols].sum(axis=1) if shopping_cols else 0
        
        # Transport
        transport_cols = [col for col in amenity_counts.columns if col in ['subway_entrance', 'bus_stop', 'station', 'public_transport']]
        scores['transport_score'] = amenity_counts[transport_cols].sum(axis=1) if transport_cols else 0
        
        # Healthcare
        health_cols = [col for col in amenity_counts.columns if col in ['hospital', 'doctors', 'pharmacy', 'clinic']]
        scores['healthcare_score'] = amenity_counts[health_cols].sum(axis=1) if health_cols else 0
        
        # Calculate overall amenity score (0-100)
        # Simple weighted approach
        scores['amenity_score'] = (
            scores['food_score'] * 0.3 + 
            scores['shopping_score'] * 0.2 + 
            scores['transport_score'] * 0.3 + 
            scores['healthcare_score'] * 0.2
        )
        
        # Normalize to 0-100
        max_score = scores['amenity_score'].max()
        if max_score > 0:
            scores['amenity_score'] = (scores['amenity_score'] / max_score) * 100
        
        scores.to_csv(processed_filename, index=False)
        
        print(f"Saved {len(df)} amenities and created scores for {len(scores)} locations")
        return df
    else:
        print("No amenities found or errors occurred.")
        return None

if __name__ == "__main__":
    fetch_osm_amenities()