import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster
import streamlit.components.v1 as components
from streamlit_folium import folium_static
import requests
import json
import os
import re
import time
from datetime import datetime, timedelta
import sys
from PIL import Image
import io
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import tempfile
import uuid

# For Prophet forecasting
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    
# For Llama integration
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(project_root)

# Ensure directories exist
os.makedirs('data/processed', exist_ok=True)
os.makedirs('data/raw', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Import utils from project if available
try:
    from src.utils.data_processor import load_land_registry_data, load_ons_rental_data, postcode_to_area
    from src.components.investment_calculator import BTRInvestmentCalculator
except ImportError:
    # Fallback implementations
    def load_land_registry_data():
        """Fallback implementation if module can't be loaded"""
        try:
            files = [f for f in os.listdir('data/processed') if f.startswith('land_registry_') and f.endswith('.csv')]
            if files:
                latest = sorted(files)[-1]
                return pd.read_csv(f'data/processed/{latest}')
            return None
        except:
            return None
            
    def load_ons_rental_data():
        """Fallback implementation if module can't be loaded"""
        try:
            files = [f for f in os.listdir('data/processed') if f.startswith('ons_rentals_') and f.endswith('.csv')]
            if files:
                latest = sorted(files)[-1]
                return pd.read_csv(f'data/processed/{latest}')
            return None
        except:
            return None
            
    def postcode_to_area(postcode):
        """Extract postcode district from a UK postcode"""
        if not isinstance(postcode, str):
            return None
        parts = postcode.strip().split(' ')
        if len(parts) > 0:
            return parts[0]
        return None
    
    class BTRInvestmentCalculator:
        """Simplified version of the investment calculator"""
        def __init__(self):
            # Default cost benchmarks (in £)
            self.cost_benchmarks = {
                'light_refurb_psf': 75,  # per sq ft
                'medium_refurb_psf': 120,
                'conversion_psf': 180,
                'new_build_psf': 225,
                'loft_extension_psf': 200,
                'kitchen': 15000,
                'bathroom': 7500
            }
            
            self.scenarios = {
                'cosmetic_refurb': {
                    'description': 'Cosmetic refurbishment only',
                    'value_uplift_pct': 0.10  # 10% value uplift
                },
                'light_refurb': {
                    'description': 'Light refurbishment',
                    'value_uplift_pct': 0.15  # 15% value uplift
                },
                'extension': {
                    'description': 'Extension (e.g. loft)',
                    'value_uplift_psf': 550  # £550 per sqft value added
                }
            }

# Styling constants
ACCENT_COLOR = "#4CAF50"  # Green accent color
SECONDARY_COLOR = "#2196F3"  # Blue for secondary elements

# Geocoding API for converting addresses to coordinates and data
def geocode_uk_address(address):
    """Convert UK address to coordinates and extract details using external API"""
    try:
        # First try to clean and format the address
        # Remove unnecessary terms to improve geocoding
        address = re.sub(r'flat\s+\d+,?\s*', '', address, flags=re.IGNORECASE)
        address = re.sub(r'apartment\s+\d+,?\s*', '', address, flags=re.IGNORECASE)
        
        # Add UK to ensure correct country context
        if not re.search(r'\buk\b|\bunitee?\s*kingdom\b', address, flags=re.IGNORECASE):
            address = f"{address}, UK"
        
        # Try with Google Maps API-like service (requires API key)
        # For demo, use OpenStreetMap Nominatim API (use with caution in production)
        url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&addressdetails=1&countrycodes=gb"
        
        # Add delay to respect usage policies
        time.sleep(1)
        
        response = requests.get(url, headers={'User-Agent': 'BTRInvestmentPlatform/1.0'})
        data = response.json()
        
        if data:
            result = data[0]
            
            # Extract details
            lat = float(result['lat'])
            lon = float(result['lon'])
            
            # Extract address components
            address_details = result.get('address', {})
            city = address_details.get('city') or address_details.get('town') or address_details.get('village')
            postcode = address_details.get('postcode', '')
            road = address_details.get('road', '')
            district = address_details.get('suburb') or address_details.get('neighbourhood') or address_details.get('district')
            county = address_details.get('county')
            
            # Create a clean formatted address
            formatted_address = result.get('display_name', address)
            
            return {
                'lat': lat,
                'lon': lon,
                'city': city,
                'postcode': postcode,
                'road': road,
                'district': district,
                'county': county,
                'formatted_address': formatted_address,
                'raw_data': result
            }
        
        return None
    except Exception as e:
        print(f"Error geocoding address: {e}")
        return None

def fetch_rental_data(postcode=None, property_type=None, bedrooms=None):
    """Fetch rental data for the area"""
    rental_data = {
        'monthly_rent': None,
        'annual_rent': None,
        'gross_yield': None,
        'growth_rate': None,
        'rental_demand': 'Medium',
        'void_periods': '2 weeks per year'
    }
    
    # Try to get data from our ONS rental data
    ons_data = load_ons_rental_data()
    
    if ons_data is not None and postcode is not None:
        # Extract postcode area
        postcode_area = postcode_to_area(postcode)
        
        # Try to find rental data for this area
        if 'region' in ons_data.columns and 'value' in ons_data.columns:
            area_data = ons_data[ons_data['region'].str.contains(postcode_area, case=False, na=False)]
            
            if len(area_data) > 0:
                # Get latest rental value
                if 'date' in area_data.columns:
                    area_data['date'] = pd.to_datetime(area_data['date'])
                    latest_data = area_data.sort_values('date', ascending=False).iloc[0]
                    rental_data['monthly_rent'] = latest_data['value']
                else:
                    rental_data['monthly_rent'] = area_data['value'].mean()
                
                # Check for growth rate
                if 'yoy_growth' in area_data.columns:
                    rental_data['growth_rate'] = area_data['yoy_growth'].mean()
    
    # Use fallback estimates if we don't have real data
    if rental_data['monthly_rent'] is None:
        # Estimate based on property type and location
        if property_type == 'F':
            rental_data['monthly_rent'] = 850
        elif property_type == 'T':
            rental_data['monthly_rent'] = 1000
        elif property_type == 'S':
            rental_data['monthly_rent'] = 1200
        elif property_type == 'D':
            rental_data['monthly_rent'] = 1500
        else:
            rental_data['monthly_rent'] = 1000
        
        # Adjust for bedrooms
        if bedrooms:
            rental_data['monthly_rent'] += (bedrooms - 2) * 150  # Adjust rent by £150 per bedroom
    
    # Calculate annual rent
    rental_data['annual_rent'] = rental_data['monthly_rent'] * 12
    
    return rental_data

def fetch_area_data(location_info):
    """Fetch data about the local area"""
    area_data = {
        'amenities': {
            'schools': [],
            'transport': [],
            'healthcare': [],
            'shops': [],
            'leisure': []
        },
        'crime_rate': None,
        'school_rating': None,
        'transport_links': None,
        'planning_applications': [],
        'area_description': None
    }
    
    # Try to get amenities from postcode
    if 'postcode' in location_info:
        postcode = location_info['postcode']
        # TODO: Implement actual data fetching from our database
    
    # Use fallback estimates for now
    area_data['crime_rate'] = 'Medium'
    area_data['school_rating'] = 'Good'
    area_data['transport_links'] = 'Average'
    
    # Add some sample amenities
    area_data['amenities']['schools'] = ['Primary School (0.3 miles)', 'Secondary School (0.8 miles)']
    area_data['amenities']['transport'] = ['Bus Stop (0.1 miles)', 'Train Station (0.7 miles)']
    area_data['amenities']['healthcare'] = ['GP Surgery (0.4 miles)', 'Hospital (2.1 miles)']
    area_data['amenities']['shops'] = ['Supermarket (0.3 miles)', 'Shopping Center (1.2 miles)']
    area_data['amenities']['leisure'] = ['Park (0.2 miles)', 'Gym (0.5 miles)']
    
    return area_data

# Here are the key functions that need error handling to prevent NoneType division errors

def calculate_renovation_scenarios(property_data):
    """Calculate renovation scenarios and their impact on value with error handling"""
    calculator = BTRInvestmentCalculator()
    
    # Ensure property_data has necessary values
    if not property_data or 'sq_ft' not in property_data or property_data['sq_ft'] is None:
        property_data['sq_ft'] = 1000  # Default value
        
    if not property_data or 'estimated_value' not in property_data or property_data['estimated_value'] is None:
        property_data['estimated_value'] = 250000  # Default value
        
    if not property_data or 'property_type' not in property_data:
        property_data['property_type'] = 'T'  # Default to terraced
    
    # Prepare scenarios
    scenarios = []
    
    # 1. Cosmetic Refurbishment
    try:
        cosmetic_cost = property_data['sq_ft'] * calculator.cost_benchmarks['light_refurb_psf'] * 0.4  # 40% of light refurb
        cosmetic_value_uplift = property_data['estimated_value'] * calculator.scenarios['cosmetic_refurb']['value_uplift_pct']
        cosmetic_new_value = property_data['estimated_value'] + cosmetic_value_uplift
        
        if cosmetic_cost > 0:  # Prevent division by zero
            roi = (cosmetic_value_uplift / cosmetic_cost - 1) * 100
        else:
            roi = 0
            
        scenarios.append({
            'name': 'Cosmetic Refurbishment',
            'description': 'Painting, decorating, minor works',
            'cost': cosmetic_cost,
            'value_uplift': cosmetic_value_uplift,
            'value_uplift_pct': calculator.scenarios['cosmetic_refurb']['value_uplift_pct'] * 100,
            'new_value': cosmetic_new_value,
            'roi': roi
        })
    except (TypeError, ZeroDivisionError):
        # Add default scenario if calculation fails
        scenarios.append({
            'name': 'Cosmetic Refurbishment',
            'description': 'Painting, decorating, minor works',
            'cost': 30000,
            'value_uplift': 25000,
            'value_uplift_pct': 10.0,
            'new_value': property_data.get('estimated_value', 250000) + 25000,
            'roi': 83.3
        })
    
    # 2. Light Refurbishment
    try:
        light_cost = property_data['sq_ft'] * calculator.cost_benchmarks['light_refurb_psf']
        light_value_uplift = property_data['estimated_value'] * calculator.scenarios['light_refurb']['value_uplift_pct']
        light_new_value = property_data['estimated_value'] + light_value_uplift
        
        if light_cost > 0:  # Prevent division by zero
            roi = (light_value_uplift / light_cost - 1) * 100
        else:
            roi = 0
            
        scenarios.append({
            'name': 'Light Refurbishment',
            'description': 'New kitchen, bathroom, and cosmetic work',
            'cost': light_cost,
            'value_uplift': light_value_uplift,
            'value_uplift_pct': calculator.scenarios['light_refurb']['value_uplift_pct'] * 100,
            'new_value': light_new_value,
            'roi': roi
        })
    except (TypeError, ZeroDivisionError):
        # Add default scenario if calculation fails
        scenarios.append({
            'name': 'Light Refurbishment',
            'description': 'New kitchen, bathroom, and cosmetic work',
            'cost': 75000,
            'value_uplift': 37500,
            'value_uplift_pct': 15.0,
            'new_value': property_data.get('estimated_value', 250000) + 37500,
            'roi': 50.0
        })
    
    # 3. Extension (if applicable to property type)
    if property_data['property_type'] in ['D', 'S', 'T']:
        try:
            # Assume extension of 20% of current sq ft
            extension_size = property_data['sq_ft'] * 0.2
            extension_cost = extension_size * calculator.cost_benchmarks['loft_extension_psf']
            extension_value = extension_size * calculator.scenarios['extension']['value_uplift_psf']
            extension_new_value = property_data['estimated_value'] + extension_value
            
            if extension_cost > 0:  # Prevent division by zero
                roi = (extension_value / extension_cost - 1) * 100
            else:
                roi = 0
                
            scenarios.append({
                'name': 'Extension',
                'description': f'Add {int(extension_size)} sq ft extension',
                'cost': extension_cost,
                'value_uplift': extension_value,
                'value_uplift_pct': (extension_value / max(property_data['estimated_value'], 1)) * 100,  # Prevent division by zero
                'new_value': extension_new_value,
                'roi': roi
            })
        except (TypeError, ZeroDivisionError):
            # Add default extension scenario if calculation fails
            extension_size = 200  # Default size
            scenarios.append({
                'name': 'Extension',
                'description': f'Add {extension_size} sq ft extension',
                'cost': 40000,
                'value_uplift': 55000,
                'value_uplift_pct': 22.0,
                'new_value': property_data.get('estimated_value', 250000) + 55000,
                'roi': 37.5
            })
    
    return scenarios


def calculate_btr_score(property_data, rental_data, area_data, location_info):
    """Calculate BTR investment score with error handling"""
    scores = {}
    
    # Ensure necessary data exists to prevent None errors
    if property_data is None:
        property_data = {}
    if rental_data is None:
        rental_data = {}
    if area_data is None:
        area_data = {}
    
    # Set default values if missing
    if 'estimated_value' not in property_data or property_data['estimated_value'] is None:
        property_data['estimated_value'] = 250000
    if 'property_type' not in property_data or property_data['property_type'] is None:
        property_data['property_type'] = 'T'  # Default to terraced
    if 'annual_rent' not in rental_data or rental_data['annual_rent'] is None:
        rental_data['annual_rent'] = 12000  # Default 1000/month
    if 'growth_rate' not in rental_data or rental_data['growth_rate'] is None:
        rental_data['growth_rate'] = 3.0  # Default 3% growth
    
    # 1. Rental Yield Score (0-25)
    try:
        if property_data['estimated_value'] > 0 and rental_data['annual_rent'] > 0:
            gross_yield = rental_data['annual_rent'] / property_data['estimated_value']
            # Scale yield score: 3% = 5 points, 5% = 15 points, 7%+ = 25 points
            yield_score = min(25, max(0, (gross_yield - 0.03) * 1250))
            scores['yield'] = yield_score
        else:
            scores['yield'] = 10  # Default
    except (TypeError, ZeroDivisionError):
        scores['yield'] = 10  # Default
    
    # 2. Property Type Score (0-20)
    property_type_scores = {
        'D': 20,  # Detached
        'S': 18,  # Semi-detached
        'T': 15,  # Terraced
        'F': 10,  # Flat/Maisonette
        'O': 5    # Other
    }
    scores['property_type'] = property_type_scores.get(property_data.get('property_type'), 10)
    
    # 3. Area Quality Score (0-20)
    # Based on amenities, school ratings, transport links
    try:
        area_score = 10  # Default
        
        # Adjust for amenities
        if 'amenities' in area_data:
            amenity_count = sum(len(amenities) for amenities in area_data['amenities'].values())
            area_score += min(5, amenity_count / 2)
        
        # Adjust for school rating
        if 'school_rating' in area_data:
            if area_data['school_rating'] == 'Outstanding':
                area_score += 5
            elif area_data['school_rating'] == 'Good':
                area_score += 3
        
        # Adjust for transport links
        if 'transport_links' in area_data:
            if area_data['transport_links'] == 'Excellent':
                area_score += 5
            elif area_data['transport_links'] == 'Good':
                area_score += 3
        
        scores['area'] = min(20, area_score)
    except (TypeError, AttributeError):
        scores['area'] = 10  # Default
    
    # 4. Growth Potential Score (0-20)
    try:
        growth_score = 10  # Default
        
        # Adjust for rental growth rate
        if 'growth_rate' in rental_data and rental_data['growth_rate'] is not None:
            # Scale: 0% = 0 points, 5% = 10 points, 10%+ = 20 points
            growth_points = min(20, max(0, rental_data['growth_rate'] * 200))
            growth_score = (growth_score + growth_points) / 2
        
        scores['growth'] = min(20, growth_score)
    except TypeError:
        scores['growth'] = 10  # Default
    
    # 5. Renovation Potential Score (0-15)
    # Older properties and certain types have more potential
    renovation_score = 7.5  # Default
    
    # Adjust for property type (houses have more potential than flats)
    if property_data.get('property_type') in ['D', 'S', 'T']:
        renovation_score += 2.5
    
    scores['renovation'] = min(15, renovation_score)
    
    # Calculate total score
    total_score = sum(scores.values())
    
    # Map to 0-100 scale
    max_possible = 25 + 20 + 20 + 20 + 15  # Sum of all max scores
    normalized_score = int(round(total_score / max_possible * 100))
    
    # Get score category
    if normalized_score >= 80:
        category = "excellent"
    elif normalized_score >= 70:
        category = "good"
    elif normalized_score >= 60:
        category = "above_average"
    elif normalized_score >= 50:
        category = "average"
    elif normalized_score >= 40:
        category = "below_average"
    elif normalized_score >= 30:
        category = "poor"
    else:
        category = "very_poor"
    
    return {
        'overall_score': normalized_score,
        'category': category,
        'component_scores': scores
    }


def fetch_property_data(postcode=None, address=None):
    """Fetch property data from Land Registry and other sources with error handling"""
    property_data = {
        'estimated_value': None,
        'property_type': None,
        'bedrooms': None,
        'bathrooms': None,
        'sq_ft': None,
        'price_history': [],
        'features': []
    }
    
    try:
        # First try to get data from our Land Registry data
        land_registry_data = load_land_registry_data()
        
        if land_registry_data is not None and postcode is not None:
            # Filter for this postcode
            properties = land_registry_data[land_registry_data['postcode'] == postcode]
            
            if len(properties) > 0:
                # Use most recent transaction
                latest_property = properties.sort_values('date_of_transfer', ascending=False).iloc[0]
                
                property_data['estimated_value'] = latest_property['price']
                property_data['property_type'] = latest_property['property_type']
                
                # Add to price history
                for _, row in properties.iterrows():
                    property_data['price_history'].append({
                        'date': row['date_of_transfer'],
                        'price': row['price']
                    })
    except Exception as e:
        print(f"Error fetching land registry data: {e}")
    
    # Use some fallback estimates if we don't have real data
    if property_data['estimated_value'] is None:
        # Realistic UK property value
        property_data['estimated_value'] = 285000  # Average UK property value
    
    if property_data['property_type'] is None:
        # Infer property type from address if possible
        if address:
            address_lower = address.lower()
            if 'flat' in address_lower or 'apartment' in address_lower:
                property_data['property_type'] = 'F'
            elif 'terrace' in address_lower:
                property_data['property_type'] = 'T'
            elif 'semi' in address_lower:
                property_data['property_type'] = 'S'
            elif 'detached' in address_lower:
                property_data['property_type'] = 'D'
            else:
                property_data['property_type'] = 'T'  # Default to terraced
        else:
            property_data['property_type'] = 'T'  # Default to terraced
    
    # Map property type code to name
    property_type_map = {
        'D': 'Detached',
        'S': 'Semi-detached',
        'T': 'Terraced',
        'F': 'Flat/Maisonette',
        'O': 'Other'
    }
    property_data['property_type_name'] = property_type_map.get(property_data['property_type'], 'Unknown')
    
    # Set reasonable defaults for missing data
    if property_data['bedrooms'] is None:
        if property_data['property_type'] == 'F':
            property_data['bedrooms'] = 2
        else:
            property_data['bedrooms'] = 3
    
    if property_data['bathrooms'] is None:
        if property_data['property_type'] == 'F':
            property_data['bathrooms'] = 1
        else:
            property_data['bathrooms'] = 1.5
    
    if property_data['sq_ft'] is None:
        if property_data['property_type'] == 'F':
            property_data['sq_ft'] = 750
        elif property_data['property_type'] == 'T':
            property_data['sq_ft'] = 1000
        elif property_data['property_type'] == 'S':
            property_data['sq_ft'] = 1200
        elif property_data['property_type'] == 'D':
            property_data['sq_ft'] = 1500
        else:
            property_data['sq_ft'] = 1000
    
    # Calculate price per sq ft
    try:
        property_data['price_per_sqft'] = property_data['estimated_value'] / property_data['sq_ft']
    except (TypeError, ZeroDivisionError):
        property_data['price_per_sqft'] = 300  # Default value
    
    # Add some property features based on property type
    if property_data['property_type'] == 'D':
        property_data['features'] = ['Garden', 'Driveway', 'Garage']
    elif property_data['property_type'] == 'S':
        property_data['features'] = ['Garden', 'Driveway']
    elif property_data['property_type'] == 'T':
        property_data['features'] = ['Garden']
    elif property_data['property_type'] == 'F':
        property_data['features'] = ['Communal Garden', 'Parking']
    
    return property_data
    
def predict_rental_growth(rental_data):
    """Predict future rental growth using Prophet or fallback method"""
    if PROPHET_AVAILABLE and rental_data.get('growth_rate') is not None:
        # Use Prophet for sophisticated forecasting
        # This would be based on historical data, which we don't fully have now
        # For now, we'll use a simplified approach
        current_rent = rental_data['monthly_rent']
        growth_rate = rental_data['growth_rate'] / 100  # Convert percentage to decimal
        
        forecast = []
        for year in range(1, 6):
            forecast.append({
                'year': year,
                'monthly_rent': current_rent * (1 + growth_rate) ** year,
                'annual_rent': current_rent * 12 * (1 + growth_rate) ** year
            })
    else:
        # Fallback to simple projection
        current_rent = rental_data['monthly_rent']
        # Use average UK rental growth of 3% if we don't have actual data
        growth_rate = rental_data.get('growth_rate', 3) / 100
        
        forecast = []
        for year in range(1, 6):
            forecast.append({
                'year': year,
                'monthly_rent': current_rent * (1 + growth_rate) ** year,
                'annual_rent': current_rent * 12 * (1 + growth_rate) ** year
            })
    
    return forecast

def generate_llama_insights(property_data, rental_data, area_data, location_info, btr_score):
    """Generate market insights using Llama 3 (if available)"""
    if not OLLAMA_AVAILABLE:
        # Fallback to predefined insights
        return {
            "investment_advice": "This property presents a solid Buy-to-Rent opportunity with potential for good rental yield and moderate capital appreciation. The area has stable demand from renters and property values have shown consistent growth.",
            "market_commentary": "The UK rental market continues to show strong demand, particularly in areas with good transport links and amenities. Rental growth has outpaced inflation in recent years, making BTR an attractive investment option.",
            "renovation_advice": "Consider focusing on kitchen and bathroom upgrades which typically offer the best return on investment for rental properties. Energy efficiency improvements can also help attract quality tenants and comply with upcoming EPC regulations."
        }
    
    # Format data for Llama
    prompt = f"""
    You are a property investment expert specializing in Buy-to-Rent (BTR) investments in the UK.
    Please provide expert insights on the following property:
    
    PROPERTY DETAILS:
    - Location: {location_info.get('formatted_address', 'Unknown')}
    - Property Type: {property_data['property_type_name']}
    - Bedrooms: {property_data['bedrooms']}
    - Bathrooms: {property_data['bathrooms']}
    - Size: {property_data['sq_ft']} sq ft
    - Estimated Value: £{property_data['estimated_value']:,.0f}
    - BTR Score: {btr_score['overall_score']}/100 ({btr_score['category'].replace('_', ' ').title()})
    
    RENTAL INFORMATION:
    - Estimated Monthly Rent: £{rental_data['monthly_rent']:,.0f}
    - Gross Yield: {(rental_data['annual_rent'] / property_data['estimated_value']) * 100:.2f}%
    - Rental Growth Rate: {rental_data.get('growth_rate', 3):.1f}%
    
    AREA INFORMATION:
    - Crime Rate: {area_data['crime_rate']}
    - School Rating: {area_data['school_rating']}
    - Transport Links: {area_data['transport_links']}
    - Key Amenities: {', '.join([item for sublist in list(area_data['amenities'].values()) for item in sublist][:5])}
    
    Based on this information, please provide:
    1. Investment Advice (2-3 sentences about whether this is a good BTR opportunity)
    2. Market Commentary (2-3 sentences about the current BTR market conditions in this area)
    3. Renovation Advice (2-3 sentences about the best renovation approach for this property)
    
    Format your response as JSON with the keys "investment_advice", "market_commentary", and "renovation_advice".
    """
    
    try:
        # Call Llama 3 via Ollama
        response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}])
        
        # Extract content
        content = response['message']['content']
        
        # Try to parse JSON from the response
        # Find JSON content between ```json and ``` if present
        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        else:
            # Assume the entire response is JSON
            json_content = content
        
        try:
            insights = json.loads(json_content)
            # Ensure all required keys are present
            required_keys = ["investment_advice", "market_commentary", "renovation_advice"]
            for key in required_keys:
                if key not in insights:
                    insights[key] = "Analysis not available."
            return insights
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "investment_advice": "This property appears to be a reasonable BTR investment opportunity based on its characteristics and location.",
                "market_commentary": "The current market shows steady demand for rental properties in this area.",
                "renovation_advice": "Focus on cost-effective improvements that enhance rental appeal and value."
            }
    except Exception as e:
        print(f"Error generating Llama insights: {e}")
        return {
            "investment_advice": "This property presents a potential BTR opportunity worth further investigation.",
            "market_commentary": "The current rental market is experiencing stable demand with moderate growth projections.",
            "renovation_advice": "Consider targeted renovations to improve rental yield while maintaining a good return on investment."
        }

def generate_pdf_report(property_data, rental_data, area_data, location_info, btr_score, renovation_scenarios, rental_forecast, llama_insights):
    """Generate a PDF report for the property"""
    # Create a temporary file
    temp_file = os.path.join(tempfile.gettempdir(), f"btr_report_{uuid.uuid4()}.pdf")
    
    # Create the PDF
    doc = SimpleDocTemplate(temp_file, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=6
    )
    
    subheading_style = ParagraphStyle(
        'Subheading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=6
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Content elements
    elements = []
    
    # Report header
    report_date = datetime.now().strftime('%b %d, %Y').upper()
    elements.append(Paragraph(f"BTR REPORT GENERATED {report_date}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Property header
    elements.append(Paragraph("The BTR Potential of", title_style))
    address = location_info.get('formatted_address', 'Unknown Address')
    elements.append(Paragraph(f"{address} is", title_style))
    elements.append(Paragraph(f"<font color={ACCENT_COLOR}>{btr_score['category'].replace('_', ' ')}.</font>", title_style))
    elements.append(Spacer(1, 12))
    
    # Property details and value
    # Current property specs
    specs_data = [
        ["Current Specs", "Estimated Value"],
        [
            f"{property_data['bedrooms']} Bed / {property_data['bathrooms']} Bath\n{property_data['sq_ft']} sqft\n£{property_data['price_per_sqft']:.0f} per sqft",
            f"£{property_data['estimated_value']:,.0f}"
        ]
    ]
    
    specs_table = Table(specs_data, colWidths=[doc.width/2.0]*2)
    specs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (1, 1), colors.white),
        ('TEXTCOLOR', (0, 1), (1, 1), colors.black),
        ('ALIGN', (1, 1), (1, 1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, 1), 'LEFT'),
        ('FONTNAME', (0, 1), (1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (1, 1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (1, 0), 1, colors.black),
        ('LINEAFTER', (0, 0), (0, 1), 1, colors.black),
    ]))
    
    elements.append(specs_table)
    elements.append(Spacer(1, 12))
    
    # BTR Score section
    elements.append(Paragraph("BTR SCORE", heading_style))
    
    # Description of the score
    score_desc = f"This {property_data['sq_ft']} sqft {property_data['property_type_name'].lower()} property has {btr_score['category']} BTR potential. "
    score_desc += f"The estimated value is £{property_data['estimated_value']:,.0f} with a potential monthly rental income of £{rental_data['monthly_rent']:,.0f}, "
    score_desc += f"giving a gross yield of {(rental_data['annual_rent'] / property_data['estimated_value']) * 100:.1f}%."
    
    elements.append(Paragraph(score_desc, normal_style))
    elements.append(Spacer(1, 6))
    
    # Investment advice from Llama
    elements.append(Paragraph("Investment Advice", subheading_style))
    elements.append(Paragraph(llama_insights['investment_advice'], normal_style))
    elements.append(Spacer(1, 6))
    
    # Market commentary
    elements.append(Paragraph("Market Commentary", subheading_style))
    elements.append(Paragraph(llama_insights['market_commentary'], normal_style))
    elements.append(Spacer(1, 12))
    
    # Renovation scenarios
    elements.append(Paragraph("RENOVATION SCENARIOS", heading_style))
    elements.append(Paragraph("Explore renovation scenarios that could increase the value of this property:", normal_style))
    elements.append(Spacer(1, 6))
    
    # Add renovation scenarios
    for scenario in renovation_scenarios:
        # Scenario header
        elements.append(Paragraph(scenario['name'], subheading_style))
        
        # Scenario details
        scenario_data = [
            [f"Cost: £{scenario['cost']:,.0f}", f"New Value: £{scenario['new_value']:,.0f}"],
            [f"Description: {scenario['description']}", f"Value uplift: £{scenario['value_uplift']:,.0f} ({scenario['value_uplift_pct']:.1f}%)"],
            [f"ROI: {scenario['roi']:.1f}%", ""]
        ]
        
        scenario_table = Table(scenario_data, colWidths=[doc.width/2.0]*2)
        scenario_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.lightgrey),
        ]))
        
        elements.append(scenario_table)
        elements.append(Spacer(1, 6))
    
    # Renovation advice
    elements.append(Paragraph("Renovation Advice", subheading_style))
    elements.append(Paragraph(llama_insights['renovation_advice'], normal_style))
    elements.append(Spacer(1, 12))
    
    # Rental forecast
    elements.append(Paragraph("RENTAL FORECAST", heading_style))
    
    # Create rental forecast table
    forecast_data = [["Year", "Monthly Rent", "Annual Rent", "Growth"]]
    
    # Current year (year 0)
    forecast_data.append([
        "Current",
        f"£{rental_data['monthly_rent']:,.0f}",
        f"£{rental_data['annual_rent']:,.0f}",
        "-"
    ])
    
    # Future years
    for i, year_data in enumerate(rental_forecast):
        growth = (year_data['monthly_rent'] / rental_data['monthly_rent']) - 1 if i == 0 else \
                 (year_data['monthly_rent'] / rental_forecast[i-1]['monthly_rent']) - 1
        
        forecast_data.append([
            f"Year {year_data['year']}",
            f"£{year_data['monthly_rent']:,.0f}",
            f"£{year_data['annual_rent']:,.0f}",
            f"{growth*100:.1f}%"
        ])
    
    forecast_table = Table(forecast_data, colWidths=[doc.width/4.0]*4)
    forecast_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEAFTER', (0, 0), (2, -1), 0.5, colors.lightgrey),
    ]))
    
    elements.append(forecast_table)
    elements.append(Spacer(1, 12))
    
    # Area information
    elements.append(Paragraph("AREA OVERVIEW", heading_style))
    
    # Create a table for area amenities
    amenities_data = []
    for category, items in area_data['amenities'].items():
        if items:
            amenities_data.append([category.title() + ":", ", ".join(items[:3])])
    
    if amenities_data:
        amenities_table = Table(amenities_data, colWidths=[doc.width*0.3, doc.width*0.7])
        amenities_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(amenities_table)
        elements.append(Spacer(1, 6))
    
    # Other area ratings
    area_ratings = [
        ["Crime Rate:", area_data['crime_rate']],
        ["School Rating:", area_data['school_rating']],
        ["Transport Links:", area_data['transport_links']]
    ]
    
    area_table = Table(area_ratings, colWidths=[doc.width*0.3, doc.width*0.7])
    area_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(area_table)
    elements.append(Spacer(1, 12))
    
    # Disclaimer
    disclaimer_text = "The accuracy of this BTR report and its applicability to your circumstances are not guaranteed. "
    disclaimer_text += "This report is offered for educational purposes only, and is not a substitute for professional advice. "
    disclaimer_text += "All figures provided are estimates only and may not reflect actual results."
    
    elements.append(Paragraph(disclaimer_text, ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.gray
    )))
    
    # Build the PDF
    doc.build(elements)
    
    return temp_file

# Streamlit UI for BTR Report Generator
def display_btr_report_generator():
    """Display the BTR Report Generator interface"""
    data_files = os.listdir('data/processed') if os.path.exists('data/processed') else []
    
    if not data_files:
        st.warning("""
        Limited data files detected. The BTR Report Generator will use estimated values for many calculations.
        For best results, run the data collection script:
        ```
        python scripts/run_data_collection.py --run-now
        ```
        """)
    st.markdown(
        """
        <style>
        .main-header {
            font-size: 3rem;
            margin-bottom: 0;
            padding-bottom: 0;
            color: black;
        }
        .highlight {
            color: #4CAF50;
            font-weight: 500;
        }
        .search-container {
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .report-header {
            background-color: #f5f5f5;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    # Header
    st.markdown("<h1 class='main-header'>Get instant <span class='highlight'>BTR potential</span> for any home.</h1>", unsafe_allow_html=True)
    
    # Search box
    st.markdown("<div class='search-container'>", unsafe_allow_html=True)
    
    address_input = st.text_input("", placeholder="SEARCH AN ADDRESS", label_visibility="collapsed")
    
    col1, col2 = st.columns([5, 1])
    
    with col2:
        generate_button = st.button("GENERATE", use_container_width=True)
    
    with col1:
        st.markdown("Enter a UK property address or postcode to generate a BTR investment report.")
    
    st.markdown("<div class='tip-container'>", unsafe_allow_html=True)
    st.info("Tip: You can search single-family homes, apartments, and multi-family properties in the UK.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Generate report when button is clicked
    if generate_button and address_input:
        with st.spinner('Analyzing property and generating BTR report...'):
            # Process the address and generate report
            try:
                # 1. Geocode the address
                location_info = geocode_uk_address(address_input)
                
                if location_info:
                    # 2. Fetch property data
                    property_data = fetch_property_data(
                        postcode=location_info.get('postcode'),
                        address=location_info.get('formatted_address')
                    )
                    
                    # 3. Fetch rental data
                    rental_data = fetch_rental_data(
                        postcode=location_info.get('postcode'),
                        property_type=property_data['property_type'],
                        bedrooms=property_data['bedrooms']
                    )
                    
                    # Calculate gross yield
                    if property_data['estimated_value'] > 0:
                        rental_data['gross_yield'] = rental_data['annual_rent'] / property_data['estimated_value']
                    else:
                        rental_data['gross_yield'] = 0.05  # Default 5%
                    
                    # 4. Fetch area data
                    area_data = fetch_area_data(location_info)
                    
                    # 5. Calculate BTR score
                    btr_score = calculate_btr_score(property_data, rental_data, area_data, location_info)
                    
                    # 6. Calculate renovation scenarios
                    renovation_scenarios = calculate_renovation_scenarios(property_data)
                    
                    # 7. Predict rental growth
                    rental_forecast = predict_rental_growth(rental_data)
                    
                    # 8. Generate Llama insights
                    llama_insights = generate_llama_insights(property_data, rental_data, area_data, location_info, btr_score)
                    
                    # 9. Generate PDF report
                    pdf_path = generate_pdf_report(
                        property_data, rental_data, area_data, location_info, 
                        btr_score, renovation_scenarios, rental_forecast, llama_insights
                    )
                    
                    # Display report summary
                    st.markdown("<div class='report-header'>", unsafe_allow_html=True)
                    
                    st.markdown(f"### BTR REPORT GENERATED {datetime.now().strftime('%b %d, %Y').upper()}")
                    
                    # Property header with details
                    st.markdown(f"# The BTR Potential of")
                    st.markdown(f"## {location_info.get('formatted_address', address_input)} is")
                    st.markdown(f"# <span class='highlight'>{btr_score['category'].replace('_', ' ')}.</span>", unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Display property details
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Current Specs")
                        st.write(f"{property_data['bedrooms']} Bed / {property_data['bathrooms']} Bath")
                        st.write(f"{property_data['sq_ft']} sqft")
                        st.write(f"£{property_data['price_per_sqft']:.0f} per sqft")
                        
                    with col2:
                        st.subheader("Estimated Value")
                        st.markdown(f"## £{property_data['estimated_value']:,.0f}")
                    
                    # Display BTR score and insights
                    st.subheader("BTR Analysis")
                    
                    with st.expander("See BTR Score Breakdown", expanded=True):
                        # Create columns for individual scores
                        score_cols = st.columns(5)
                        
                        with score_cols[0]:
                            st.metric("Yield", f"{btr_score['component_scores']['yield']:.1f}/25")
                        
                        with score_cols[1]:
                            st.metric("Property", f"{btr_score['component_scores']['property_type']:.1f}/20")
                        
                        with score_cols[2]:
                            st.metric("Area", f"{btr_score['component_scores']['area']:.1f}/20")
                        
                        with score_cols[3]:
                            st.metric("Growth", f"{btr_score['component_scores']['growth']:.1f}/20")
                        
                        with score_cols[4]:
                            st.metric("Renovation", f"{btr_score['component_scores']['renovation']:.1f}/15")
                        
                        # Overview text
                        st.write(f"This {property_data['sq_ft']} sqft {property_data['property_type_name'].lower()} has {btr_score['category']} BTR potential with an overall score of {btr_score['overall_score']}/100.")
                    
                    # Expert insights section
                    st.subheader("Expert Insights")
                    
                    with st.expander("Investment Advice", expanded=True):
                        st.write(llama_insights['investment_advice'])
                    
                    with st.expander("Market Commentary", expanded=True):
                        st.write(llama_insights['market_commentary'])
                    
                    with st.expander("Renovation Advice", expanded=True):
                        st.write(llama_insights['renovation_advice'])
                    
                    # Renovation scenarios section
                    st.subheader("Renovation Scenarios")
                    
                    for i, scenario in enumerate(renovation_scenarios):
                        with st.expander(f"{scenario['name']} (+{scenario['value_uplift_pct']:.1f}%)", expanded=i==0):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Cost:** £{scenario['cost']:,.0f}")
                                st.write(f"**Description:** {scenario['description']}")
                                st.write(f"**ROI:** {scenario['roi']:.1f}%")
                            
                            with col2:
                                st.write(f"**New Value:** £{scenario['new_value']:,.0f}")
                                st.write(f"**Value Uplift:** £{scenario['value_uplift']:,.0f} ({scenario['value_uplift_pct']:.1f}%)")
                    
                    # Rental projection section
                    st.subheader("Rental Forecast")
                    
                    # Create data for chart
                    forecast_df = pd.DataFrame({
                        'Year': ['Current'] + [f"Year {year['year']}" for year in rental_forecast],
                        'Monthly Rent': [rental_data['monthly_rent']] + [year['monthly_rent'] for year in rental_forecast]
                    })
                    
                    # Create chart
                    fig = px.bar(
                        forecast_df,
                        x='Year',
                        y='Monthly Rent',
                        title='Projected Monthly Rental Income',
                        color_discrete_sequence=[ACCENT_COLOR]
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Area overview section
                    st.subheader("Area Overview")
                    
                    # Create a simple map
                    if 'lat' in location_info and 'lon' in location_info:
                        m = folium.Map(location=[location_info['lat'], location_info['lon']], zoom_start=15)
                        
                        # Add property marker
                        folium.Marker(
                            location=[location_info['lat'], location_info['lon']],
                            popup=location_info.get('formatted_address', 'Property Location'),
                            icon=folium.Icon(color='green', icon='home', prefix='fa')
                        ).add_to(m)
                        
                        # Add a circle to show the area
                        folium.Circle(
                            location=[location_info['lat'], location_info['lon']],
                            radius=400,  # 400m radius
                            color=ACCENT_COLOR,
                            fill=True,
                            fill_color=ACCENT_COLOR,
                            fill_opacity=0.2
                        ).add_to(m)
                        
                        # Display map
                        folium_static(m)
                    
                    # Area amenities
                    amenity_cols = st.columns(3)
                    
                    amenity_categories = list(area_data['amenities'].keys())
                    for i, category in enumerate(amenity_categories):
                        col_idx = i % 3
                        with amenity_cols[col_idx]:
                            st.write(f"**{category.title()}:**")
                            for item in area_data['amenities'][category]:
                                st.write(f"- {item}")
                    
                    # Area ratings
                    st.write(f"**Crime Rate:** {area_data['crime_rate']}")
                    st.write(f"**School Rating:** {area_data['school_rating']}")
                    st.write(f"**Transport Links:** {area_data['transport_links']}")
                    
                    # Download report button
                    if pdf_path:
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                        
                        st.download_button(
                            label="Download BTR Report (PDF)",
                            data=pdf_bytes,
                            file_name=f"BTR_Report_{location_info.get('postcode', '').replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )
                    
                    # Button to generate a new report
                    st.button("Generate Another Report", on_click=lambda: st.experimental_rerun())
                else:
                    st.error("Could not find location information for the provided address. Please try a different address or format.")
            except Exception as e:
                st.error(f"An error occurred while generating the report: {str(e)}")
    
    # Bottom section - What's next
    if not (generate_button and address_input):
        st.subheader("What is a BTR Investment Report?")
        st.write("""
        Our BTR (Buy-to-Rent) Investment Report provides a comprehensive analysis of a property's potential as a rental investment. 
        The report includes:
        
        - Property valuation and specifications
        - Rental income potential and yield calculations
        - Area analysis with amenities and transportation
        - Renovation scenarios and their impact on value
        - Future rental income projections
        - Expert insights on the investment potential
        
        Simply enter a UK property address or postcode above and click "GENERATE" to get your free report.
        """)

# Main app
def main():
    st.set_page_config(
        page_title="BTR Investment Report Generator",
        page_icon="🏘️",
        layout="wide"
    )
    
    # Create sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select a page",
        ["BTR Report Generator", "BTR Hotspot Map", "Investment Calculator", "Data Explorer"]
    )
    
    # Display the selected page
    if page == "BTR Report Generator":
        display_btr_report_generator()
    elif page == "BTR Hotspot Map":
        # Import and use the existing map function if available
        try:
            from src.components.mapping_util import display_btr_map
            display_btr_map()
        except ImportError:
            st.write("BTR Hotspot Map is not available. Please check back later.")
    elif page == "Investment Calculator":
        # Import and use the existing calculator if available
        try:
            from src.components.investment_calculator_page import display_investment_calculator
            display_investment_calculator()
        except ImportError:
            st.write("Investment Calculator is not available. Please check back later.")
    elif page == "Data Explorer":
        # Import and use the existing data dashboard if available
        try:
            from src.components.data_dashboard import display_data_dashboard
            display_data_dashboard()
        except ImportError:
            st.write("Data Explorer is not available. Please check back later.")

if __name__ == "__main__":
    main()