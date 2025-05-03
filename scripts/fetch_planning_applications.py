import requests
import logging
import pandas as pd
import os
import json
from datetime import datetime

def fetch_planning_applications():
    """
    Fetch planning applications using the Planning Data API with simpler queries
    """
    logging.info("Fetching planning applications...")
    
    # Base URL for the Planning Data API
    base_url = "https://www.planning.data.gov.uk"
    
    # Define locations by LPA codes instead of geometries
    locations = {
        "manchester": "E08000003",  # Manchester LPA code
        "birmingham": "E08000025",  # Birmingham LPA code
        "london_camden": "E09000007",  # Camden LPA code
        "london_westminster": "E09000033"  # Westminster LPA code
    }
    
    all_planning_data = []
    
    try:
        for location_name, lpa_code in locations.items():
            logging.info(f"Fetching planning applications for {location_name}...")
            
            # Use a simpler query with just the LPA code and no geometry
            params = {
                "limit": 50,  # Restrict to 50 records per location
                "lpaCodes": lpa_code
            }
            
            # Make the API request
            url = f"{base_url}/dataset/planning-application.json"
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                logging.warning(f"Error fetching planning data for {location_name}: {response.status_code}")
                continue
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                logging.warning(f"Error parsing JSON for {location_name}")
                continue
            
            records = data.get("items", [])
            
            if not records:
                logging.warning(f"No planning applications found for {location_name}")
                continue
            
            logging.info(f"Found {len(records)} planning applications for {location_name}")
            
            # Add location name to each record
            for record in records:
                record["location"] = location_name
                all_planning_data.append(record)
        
        if all_planning_data:
            # Save the data to a CSV file
            output_dir = "data/raw"
            os.makedirs(output_dir, exist_ok=True)
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{output_dir}/planning_applications_{date_str}.csv"
            
            # Convert to DataFrame and save
            df = pd.DataFrame(all_planning_data)
            df.to_csv(filename, index=False)
            
            logging.info(f"Saved {len(df)} planning applications to {filename}")
            return df
        else:
            logging.warning("No planning applications found across all areas")
            return None
    
    except Exception as e:
        logging.error(f"Error fetching planning applications: {str(e)}")
        return None