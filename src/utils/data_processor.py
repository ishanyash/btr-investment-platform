import pandas as pd
import numpy as np
import os
from datetime import datetime

def get_latest_file(directory, prefix):
    """Get the most recent data file with the given prefix"""
    files = [f for f in os.listdir(directory) if f.startswith(prefix) and f.endswith('.csv')]
    if not files:
        return None
    
    # Sort by date in filename (assuming format prefix_YYYYMMDD.csv)
    latest_file = sorted(files)[-1]
    return os.path.join(directory, latest_file)

def load_land_registry_data():
    """Load the most recent Land Registry data"""
    filename = get_latest_file('data/processed', 'land_registry_')
    if not filename:
        return None
    
    return pd.read_csv(filename)

def load_ons_rental_data():
    """Load the most recent ONS rental data"""
    filename = get_latest_file('data/processed', 'ons_rentals_')
    if not filename:
        return None
    
    return pd.read_csv(filename)

def load_planning_data():
    """Load the most recent planning applications data"""
    filename = get_latest_file('data/processed', 'planning_applications_')
    if not filename:
        return None
    
    return pd.read_csv(filename)

def load_amenities_data():
    """Load the most recent OSM amenities data"""
    filename = get_latest_file('data/processed', 'osm_amenities_')
    if not filename:
        return None
    
    return pd.read_csv(filename)

def load_epc_data():
    """Load the most recent EPC ratings data"""
    filename = get_latest_file('data/processed', 'epc_ratings_')
    if not filename:
        return None
    
    return pd.read_csv(filename)

def postcode_to_area(postcode):
    """Extract area from a UK postcode"""
    if not isinstance(postcode, str):
        return None
    
    # UK postcodes typically have format: AA9A 9AA or A9A 9AA
    # The first part before the space is the outward code
    parts = postcode.strip().split(' ')
    if len(parts) > 0:
        return parts[0]
    return None

def calculate_investment_score(property_data, rental_data=None, amenities_data=None, epc_data=None):
    """
    Calculate investment score for BTR properties
    
    This is a simplified scoring function that will be expanded in Week 2
    """
    # Start with base score
    property_data['base_score'] = 50
    
    # Adjust score based on property type (houses often perform better for BTR)
    type_scores = {
        'D': 20,  # Detached
        'S': 15,  # Semi-detached
        'T': 10,  # Terraced
        'F': 5,   # Flat
        'O': 0    # Other
    }
    
    if 'property_type' in property_data.columns:
        property_data['type_score'] = property_data['property_type'].map(type_scores).fillna(0)
        property_data['base_score'] += property_data['type_score']
    
    # If we have rental data, integrate it
    if rental_data is not None and 'postcode' in property_data.columns:
        # Extract postcode area
        property_data['postcode_area'] = property_data['postcode'].apply(postcode_to_area)
        
        # This would need to be implemented based on your actual data structure
        # For now, just a placeholder
        property_data['rental_score'] = 0
    
    # Limit final score to 0-100
    property_data['investment_score'] = property_data['base_score'].clip(0, 100)
    
    return property_data

def create_master_dataset():
    """
    Integrate data from all sources into a master dataset
    """
    # Load all datasets
    land_registry = load_land_registry_data()
    ons_rentals = load_ons_rental_data()
    planning = load_planning_data()
    amenities = load_amenities_data()
    epc = load_epc_data()
    
    if land_registry is None:
        return None
    
    # Calculate investment scores
    scored_data = calculate_investment_score(
        land_registry,
        rental_data=ons_rentals,
        amenities_data=amenities,
        epc_data=epc
    )
    
    # Save the master dataset
    today = datetime.now().strftime('%Y%m%d')
    output_file = f"data/processed/master_dataset_{today}.csv"
    scored_data.to_csv(output_file, index=False)
    
    return scored_data