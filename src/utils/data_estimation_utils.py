import time
import os
import json
import pandas as pd
import numpy as np
import hashlib
import re

# Cache directory
CACHE_DIR = "data/cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_key(address):
    """Generate a cache key from an address"""
    return hashlib.md5(address.lower().encode()).hexdigest()

def get_cached_data(address, data_type, max_age_days=30):
    """Get data from cache if available and not expired"""
    cache_key = get_cache_key(address)
    cache_file = f"{CACHE_DIR}/{cache_key}_{data_type}.json"
    
    if os.path.exists(cache_file):
        # Check if cache is still valid
        file_time = os.path.getmtime(cache_file)
        age_days = (time.time() - file_time) / (60 * 60 * 24)
        
        if age_days <= max_age_days:
            with open(cache_file, 'r') as f:
                return json.load(f)
    
    return None

def save_to_cache(address, data_type, data):
    """Save data to cache"""
    cache_key = get_cache_key(address)
    cache_file = f"{CACHE_DIR}/{cache_key}_{data_type}.json"
    
    with open(cache_file, 'w') as f:
        json.dump(data, f)

def estimate_property_value(location_info, property_type=None, bedrooms=None):
    """Estimate property value based on location and characteristics"""
    # Default to middle-range UK property value
    base_value = 285000
    
    # Adjust based on location
    area_multipliers = {
        'LONDON': 2.5,
        'MANCHESTER': 1.2,
        'BIRMINGHAM': 1.1,
        'LEEDS': 1.0,
        'BRISTOL': 1.3,
        'EDINBURGH': 1.4,
        'GLASGOW': 0.9,
        'CARDIFF': 1.0,
        'LIVERPOOL': 0.8,
        'NEWCASTLE': 0.8,
        'NOTTINGHAM': 0.9,
        'SHEFFIELD': 0.8,
        'BELFAST': 0.7,
    }
    
    # Try to match location to known areas
    area_multiplier = 1.0
    location = location_info.get('formatted_address', '').upper()
    
    for area, multiplier in area_multipliers.items():
        if area in location:
            area_multiplier = multiplier
            break
    
    # Adjust for postcode if available
    postcode = location_info.get('postcode', '')
    if postcode:
        # London premium postcodes
        if re.match(r'^(SW[1-7]|W[1-2]|WC[1-2]|EC[1-4]|NW[1-3,8])', postcode):
            area_multiplier = max(area_multiplier, 3.0)
        # Other premium areas
        elif re.match(r'^(GU|RG|OX|BH|BN|BS|B9[1-9]|M21)', postcode):
            area_multiplier = max(area_multiplier, 1.5)
    
    # Apply location multiplier
    estimated_value = base_value * area_multiplier
    
    # Adjust for property type
    if property_type:
        type_multipliers = {
            'D': 1.3,  # Detached
            'S': 1.0,  # Semi-detached
            'T': 0.85, # Terraced
            'F': 0.7   # Flat
        }
        estimated_value *= type_multipliers.get(property_type, 1.0)
    
    # Adjust for number of bedrooms
    if bedrooms:
        # Base on 3-bedroom as standard
        bedroom_adjustment = 1.0 + (bedrooms - 3) * 0.15
        estimated_value *= max(0.75, bedroom_adjustment)  # Minimum 0.75x for studios/1-beds
    
    return round(estimated_value, -3)  # Round to nearest thousand

def estimate_rental_income(property_data, location_info):
    """Estimate rental income based on property value and location"""
    property_type = property_data.get('property_type', 'T')  # Default to terraced
    estimated_value = property_data.get('estimated_value', 0)
    
    # Base yields by property type (conservative estimates)
    base_yields = {
        'D': 0.040,  # Detached: 4.0%
        'S': 0.045,  # Semi: 4.5%
        'T': 0.050,  # Terraced: 5.0%
        'F': 0.055   # Flat: 5.5%
    }
    
    # Location adjustments for rental yields
    area_adjustments = {
        'LONDON': -0.010,     # Lower yields in London
        'MANCHESTER': 0.008,  # Higher yields in Manchester
        'BIRMINGHAM': 0.007,
        'LIVERPOOL': 0.012,   # Higher yields in Liverpool
        'LEEDS': 0.005,
        'SHEFFIELD': 0.010,
        'NEWCASTLE': 0.010,
        'GLASGOW': 0.008,
        'EDINBURGH': -0.005,  # Lower yields in Edinburgh
        'BRISTOL': -0.002,
        'CARDIFF': 0.005,
        'BELFAST': 0.010
    }
    
    # Get base yield
    base_yield = base_yields.get(property_type, 0.05)
    
    # Apply area adjustment
    location = location_info.get('formatted_address', '').upper()
    for area_name, adjustment in area_adjustments.items():
        if area_name in location:
            base_yield += adjustment
            break
    
    # Calculate rental values
    annual_rent = estimated_value * base_yield
    monthly_rent = annual_rent / 12
    
    # Round to nearest £10
    monthly_rent = round(monthly_rent, -1)
    annual_rent = monthly_rent * 12
    
    return {
        'monthly_rent': monthly_rent,
        'annual_rent': annual_rent,
        'gross_yield': base_yield,
        'growth_rate': estimate_rental_growth_rate(location_info),
        'rental_demand': estimate_rental_demand(location_info),
        'void_periods': '2-3 weeks per year',
        'data_quality': 'estimated'
    }

def estimate_rental_growth_rate(location_info):
    """Estimate annual rental growth rate for the area"""
    # Default UK average rental growth
    base_growth = 3.0  # 3.0%
    
    # Location-specific adjustments
    location = location_info.get('formatted_address', '').upper()
    growth_adjustments = {
        'LONDON': 1.0,      # Higher growth in London
        'MANCHESTER': 1.5,  # Strong growth in Manchester
        'BIRMINGHAM': 1.0,
        'BRISTOL': 1.0,
        'EDINBURGH': 0.5,
        'LEEDS': 0.5,
        'LIVERPOOL': 0.0,
        'NEWCASTLE': -0.5,  # Slower growth
        'GLASGOW': 0.0,
        'CARDIFF': 0.0,
        'BELFAST': -0.5,
        'SHEFFIELD': 0.0
    }
    
    # Apply adjustment if location matches
    for area, adjustment in growth_adjustments.items():
        if area in location:
            base_growth += adjustment
            break
    
    return base_growth

def estimate_rental_demand(location_info):
    """Estimate rental demand in the area (High/Medium/Low)"""
    location = location_info.get('formatted_address', '').upper()
    
    # High demand areas
    high_demand = ['LONDON', 'MANCHESTER', 'BIRMINGHAM', 'EDINBURGH', 'BRISTOL', 'LEEDS']
    # Low demand areas
    low_demand = ['BLACKPOOL', 'WIGAN', 'HULL', 'STOKE']
    
    # Check if location matches any high demand areas
    for area in high_demand:
        if area in location:
            return "High"
    
    # Check if location matches any low demand areas
    for area in low_demand:
        if area in location:
            return "Low"
    
    # Default to medium demand
    return "Medium"

def estimate_area_data(location_info):
    """Estimate area data based on location"""
    location = location_info.get('formatted_address', '').upper()
    
    # Default area characteristics
    area_data = {
        'amenities': {
            'schools': [],
            'transport': [],
            'healthcare': [],
            'shops': [],
            'leisure': []
        },
        'crime_rate': 'Medium',
        'school_rating': 'Good',
        'transport_links': 'Average',
        'planning_applications': [],
        'area_description': None,
        'data_quality': 'estimated'
    }
    
    # Crime rate estimation
    crime_rates = {
        'LONDON': 'Medium-High',
        'MANCHESTER': 'Medium-High',
        'LIVERPOOL': 'Medium-High',
        'BIRMINGHAM': 'Medium-High',
        'LEEDS': 'Medium',
        'SHEFFIELD': 'Medium-Low',
        'EDINBURGH': 'Low',
        'CARDIFF': 'Medium-Low',
        'BRISTOL': 'Medium',
        'GLASGOW': 'Medium',
        'BELFAST': 'Medium',
        'CAMBRIDGE': 'Low',
        'OXFORD': 'Low'
    }
    
    # School rating estimation
    school_ratings = {
        'LONDON': 'Good',
        'MANCHESTER': 'Good',
        'CAMBRIDGE': 'Outstanding',
        'OXFORD': 'Outstanding',
        'EDINBURGH': 'Very Good',
        'BRISTOL': 'Good',
        'BIRMINGHAM': 'Good',
        'LEEDS': 'Good',
        'LIVERPOOL': 'Satisfactory',
        'GLASGOW': 'Good',
        'CARDIFF': 'Good',
        'BELFAST': 'Good'
    }
    
    # Transport links estimation
    transport_links = {
        'LONDON': 'Excellent',
        'MANCHESTER': 'Very Good',
        'BIRMINGHAM': 'Good',
        'LEEDS': 'Good',
        'LIVERPOOL': 'Good',
        'EDINBURGH': 'Good',
        'GLASGOW': 'Good',
        'BRISTOL': 'Good',
        'CARDIFF': 'Satisfactory',
        'BELFAST': 'Satisfactory',
        'SHEFFIELD': 'Satisfactory',
        'NEWCASTLE': 'Satisfactory'
    }
    
    # Update area data based on location
    for area, rating in crime_rates.items():
        if area in location:
            area_data['crime_rate'] = rating
            break
    
    for area, rating in school_ratings.items():
        if area in location:
            area_data['school_rating'] = rating
            break
    
    for area, rating in transport_links.items():
        if area in location:
            area_data['transport_links'] = rating
            break
    
    # Add generic amenities based on typical urban/suburban profiles
    if any(city in location for city in ['LONDON', 'MANCHESTER', 'BIRMINGHAM', 'LEEDS', 'LIVERPOOL', 'GLASGOW', 'EDINBURGH']):
        # Urban profile
        area_data['amenities'] = {
            'schools': ['Primary School (0.3 miles)', 'Secondary School (0.8 miles)'],
            'transport': ['Bus Stop (0.1 miles)', 'Train Station (0.5 miles)', 'Underground Station (0.7 miles)'],
            'healthcare': ['GP Surgery (0.4 miles)', 'Pharmacy (0.3 miles)', 'Hospital (1.8 miles)'],
            'shops': ['Supermarket (0.2 miles)', 'Shopping Center (1.0 miles)', 'Convenience Store (0.1 miles)'],
            'leisure': ['Park (0.4 miles)', 'Gym (0.5 miles)', 'Restaurant (0.2 miles)', 'Cafe (0.1 miles)']
        }
    else:
        # Suburban/rural profile
        area_data['amenities'] = {
            'schools': ['Primary School (0.6 miles)', 'Secondary School (1.5 miles)'],
            'transport': ['Bus Stop (0.3 miles)', 'Train Station (2.1 miles)'],
            'healthcare': ['GP Surgery (0.8 miles)', 'Pharmacy (0.7 miles)', 'Hospital (4.2 miles)'],
            'shops': ['Supermarket (0.7 miles)', 'Convenience Store (0.4 miles)'],
            'leisure': ['Park (0.7 miles)', 'Gym (1.2 miles)', 'Restaurant (0.8 miles)']
        }
    
    return area_data

def estimate_epc_rating(property_data):
    """Estimate EPC rating based on property characteristics"""
    property_type = property_data.get('property_type', 'T')
    property_age = property_data.get('construction_age_band', None)
    
    # Default ratings by property type (if age unknown)
    default_ratings = {
        'D': 'D',  # Detached
        'S': 'D',  # Semi
        'T': 'E',  # Terraced
        'F': 'C'   # Flat (often newer)
    }
    
    # Return default if no age information
    if not property_age:
        return {
            'current_energy_rating': default_ratings.get(property_type, 'D'),
            'potential_energy_rating': 'B',
            'current_energy_efficiency': 60,
            'potential_energy_efficiency': 85,
            'efficiency_improvement': 25,
            'data_quality': 'estimated'
        }
    
    # More sophisticated estimation can be added based on age, etc.
    return {
        'current_energy_rating': default_ratings.get(property_type, 'D'),
        'potential_energy_rating': 'B',
        'current_energy_efficiency': 60,
        'potential_energy_efficiency': 85,
        'efficiency_improvement': 25,
        'data_quality': 'estimated'
    }

def add_data_quality_indicators(report_data):
    """Add data quality indicators to the report"""
    quality_indicators = {
        'verified': '✓',    # Verified data
        'estimated': '≈',   # Estimated data
        'ai_generated': '🤖' # AI-generated content
    }
    
    # Add indicators to each section
    for section_name, section_data in report_data.items():
        if isinstance(section_data, dict) and 'data_quality' in section_data:
            quality = section_data['data_quality']
            section_data['quality_indicator'] = quality_indicators.get(quality, '')
    
    return report_data