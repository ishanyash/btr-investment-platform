import pandas as pd
import numpy as np
from collections import defaultdict

def calculate_location_score(location_data, amenities_data=None, rental_data=None, 
                             epc_data=None, land_registry_data=None, planning_data=None):
    """
    Calculate a comprehensive BTR location score (0-100) based on multiple data sources
    
    Parameters:
    -----------
    location_data : str or dict
        Either a location name (string) or dictionary with details like postcode, coordinates
    amenities_data : DataFrame
        OSM amenities data
    rental_data : DataFrame
        ONS rental data
    epc_data : DataFrame
        EPC ratings data
    land_registry_data : DataFrame
        Land Registry price data
    planning_data : DataFrame
        Planning applications data
    
    Returns:
    --------
    dict
        Dictionary with overall score and component scores
    """
    scores = defaultdict(float)
    weights = defaultdict(float)
    
    # Base score starts at 50
    scores['base'] = 50
    weights['base'] = 1.0
    
    # Extract location identifier (could be name, postcode area, etc.)
    location_id = location_data
    if isinstance(location_data, dict):
        location_id = location_data.get('name') or location_data.get('postcode')
    
    # 1. Amenities score (0-20)
    if amenities_data is not None:
        amenity_score = calculate_amenity_score(location_id, amenities_data)
        scores['amenities'] = amenity_score
        weights['amenities'] = 0.2
    
    # 2. Rental market score (0-25)
    if rental_data is not None:
        rental_score = calculate_rental_score(location_id, rental_data)
        scores['rental'] = rental_score
        weights['rental'] = 0.25
    
    # 3. Property value score (0-20)
    if land_registry_data is not None:
        value_score = calculate_property_value_score(location_id, land_registry_data)
        scores['property_value'] = value_score
        weights['property_value'] = 0.2
    
    # 4. Growth potential score (0-20)
    if planning_data is not None and land_registry_data is not None:
        growth_score = calculate_growth_potential(location_id, planning_data, land_registry_data)
        scores['growth'] = growth_score
        weights['growth'] = 0.2
    
    # 5. Energy efficiency score (0-15)
    if epc_data is not None:
        efficiency_score = calculate_efficiency_score(location_id, epc_data)
        scores['efficiency'] = efficiency_score
        weights['efficiency'] = 0.15
    
    # Calculate weighted score
    total_weight = sum(weights.values())
    weighted_score = sum(scores[k] * weights[k] for k in scores) / total_weight
    
    # Round to nearest integer and ensure within 0-100 range
    final_score = int(round(min(max(weighted_score, 0), 100)))
    
    return {
        'overall_score': final_score,
        'component_scores': dict(scores),
        'location': location_id
    }

def calculate_amenity_score(location_id, amenities_data):
    """Calculate score based on amenities (0-20)"""
    try:
        # Try to filter amenities for this location
        location_amenities = amenities_data[amenities_data['location'] == location_id]
        
        if len(location_amenities) == 0:
            return 10  # Default score if no data
        
        # Use amenity_score if available
        if 'amenity_score' in location_amenities.columns:
            # Normalize to 0-20 scale
            return min(location_amenities['amenity_score'].mean() / 5, 20)
        
        # Otherwise calculate from components if available
        score = 0
        if 'food_score' in location_amenities.columns:
            score += min(location_amenities['food_score'].mean() / 10, 5)  # Max 5 points
        
        if 'transport_score' in location_amenities.columns:
            score += min(location_amenities['transport_score'].mean() / 10, 6)  # Max 6 points
        
        if 'shopping_score' in location_amenities.columns:
            score += min(location_amenities['shopping_score'].mean() / 10, 4)  # Max 4 points
        
        if 'healthcare_score' in location_amenities.columns:
            score += min(location_amenities['healthcare_score'].mean() / 10, 5)  # Max 5 points
        
        return score
        
    except Exception as e:
        print(f"Error calculating amenity score: {e}")
        return 10  # Default score
    
def calculate_rental_score(location_id, rental_data):
    """Calculate score based on rental market (0-25)"""
    try:
        # Filter for relevant region
        # Normalize region names as needed
        rental_info = rental_data
        
        if 'region' in rental_data.columns:
            # Try exact match first
            region_data = rental_data[rental_data['region'] == location_id]
            
            # If no exact match, try substring match
            if len(region_data) == 0:
                for region in rental_data['region'].unique():
                    if location_id in region or region in location_id:
                        region_data = rental_data[rental_data['region'] == region]
                        break
            
            if len(region_data) > 0:
                rental_info = region_data
        
        # Calculate score components
        score = 12.5  # Start at middle of range
        
        # Adjust based on current rental value
        if 'value' in rental_info.columns:
            # Normalize relative to national average
            avg_value = rental_data['value'].mean()
            location_value = rental_info['value'].mean()
            
            # Higher values = better score (up to a limit)
            value_ratio = location_value / avg_value
            if value_ratio > 0.8:  # Only reward if at least 80% of national average
                value_score = min((value_ratio - 0.8) * 50, 5)  # Max 5 points
                score += value_score
        
        # Adjust based on year-on-year growth
        if 'yoy_growth' in rental_info.columns:
            avg_growth = max(1, rental_data['yoy_growth'].mean())  # Avoid division by zero
            location_growth = max(0, rental_info['yoy_growth'].mean())  # Ensure non-negative
            
            # Higher growth = better score
            growth_ratio = location_growth / avg_growth
            growth_score = min(growth_ratio * 10, 7.5)  # Max 7.5 points
            score += growth_score
        
        return score
    
    except Exception as e:
        print(f"Error calculating rental score: {e}")
        return 12.5  # Default score is middle of range
    
def calculate_property_value_score(location_id, land_registry_data):
    """Calculate score based on property values (0-20)"""
    try:
        # Extract postcode area/district if location is a full postcode
        postcode_area = location_id
        if ' ' in location_id:
            postcode_area = location_id.split(' ')[0]
        
        # Filter for this location's properties
        location_properties = land_registry_data[
            land_registry_data['postcode'].str.startswith(postcode_area, na=False)
        ]
        
        if len(location_properties) == 0:
            return 10  # Default score
        
        # Calculate price metrics
        avg_price = location_properties['price'].mean()
        national_avg = land_registry_data['price'].mean()
        
        # Calculate price per square foot if data available
        price_psf = None
        if 'floor_area' in location_properties.columns:
            price_psf = avg_price / location_properties['floor_area'].mean()
        
        # Calculate score components
        score = 10  # Start in the middle
        
        # Adjust based on relative price (higher values better for BTR up to a point)
        price_ratio = avg_price / national_avg
        if price_ratio < 0.5:  # Too cheap may indicate poor location
            score -= min((0.5 - price_ratio) * 20, 5)
        elif price_ratio > 2.0:  # Too expensive may limit rental yield
            score -= min((price_ratio - 2.0) * 5, 5)
        else:  # Sweet spot between 0.5-2.0x national average
            # Ideal is 1.0-1.5x national average
            if price_ratio > 1.0 and price_ratio < 1.5:
                score += 5
            else:
                score += 2.5
        
        # Adjust based on property types in the area
        if 'property_type' in location_properties.columns:
            # BTR favors areas with mix of property types
            type_counts = location_properties['property_type'].value_counts(normalize=True)
            
            # Calculate diversity score (0-5)
            unique_types = len(type_counts)
            diversity_score = min(unique_types * 1.25, 5)
            score += diversity_score
            
            # Favor areas with higher proportion of houses vs flats for SFH BTR
            if 'F' in type_counts and ('D' in type_counts or 'S' in type_counts or 'T' in type_counts):
                house_ratio = 1 - type_counts.get('F', 0)
                house_score = min(house_ratio * 5, 5)
                score += house_score
        
        return min(max(score, 0), 20)
    
    except Exception as e:
        print(f"Error calculating property value score: {e}")
        return 10  # Default score
    
def calculate_growth_potential(location_id, planning_data, land_registry_data):
    """Calculate score based on growth potential (0-20)"""
    try:
        growth_score = 10  # Start in the middle
        
        # 1. Check planning applications
        if planning_data is not None:
            # Extract postcode district/area
            postcode_area = location_id
            if ' ' in location_id:
                postcode_area = location_id.split(' ')[0]
            
            # Filter for this location
            location_planning = planning_data[
                planning_data['address'].str.contains(postcode_area, case=False, na=False)
            ]
            
            if len(location_planning) > 0:
                # Calculate residential development intensity
                if 'is_residential' in location_planning.columns:
                    residential_apps = location_planning[location_planning['is_residential'] == True]
                    residential_ratio = len(residential_apps) / len(location_planning)
                    
                    # Higher ratio of residential applications = more growth potential
                    residential_score = min(residential_ratio * 10, 5)
                    growth_score += residential_score
                
                # Calculate new units being added
                if 'unit_count' in location_planning.columns:
                    total_new_units = location_planning['unit_count'].sum()
                    # Scale number of units (more units = more growth)
                    unit_score = min(total_new_units / 100, 5)  # Cap at 500 units for max score
                    growth_score += unit_score
        
        # 2. Check price growth trends
        if land_registry_data is not None and 'date_of_transfer' in land_registry_data.columns:
            # Extract postcode area
            postcode_area = location_id
            if ' ' in location_id:
                postcode_area = location_id.split(' ')[0]
            
            # Filter for this location
            location_sales = land_registry_data[
                land_registry_data['postcode'].str.startswith(postcode_area, na=False)
            ]
            
            if len(location_sales) > 0:
                # Convert dates and sort
                location_sales['date_of_transfer'] = pd.to_datetime(location_sales['date_of_transfer'])
                location_sales = location_sales.sort_values('date_of_transfer')
                
                # Calculate price growth over time
                if len(location_sales) > 10:  # Need sufficient data
                    # Group by year and month
                    location_sales['year_month'] = location_sales['date_of_transfer'].dt.to_period('M')
                    monthly_prices = location_sales.groupby('year_month')['price'].mean()
                    
                    if len(monthly_prices) > 1:
                        # Calculate monthly growth rate
                        earliest = monthly_prices.iloc[0]
                        latest = monthly_prices.iloc[-1]
                        months = len(monthly_prices)
                        
                        if earliest > 0:
                            # Compound monthly growth rate
                            monthly_growth = (latest / earliest) ** (1 / months) - 1
                            annual_growth = (1 + monthly_growth) ** 12 - 1
                            
                            # Score based on annual growth (0-10)
                            # 3% is average, 7%+ is excellent
                            growth_score += min(annual_growth * 100, 10)
        
        return min(max(growth_score, 0), 20)
    
    except Exception as e:
        print(f"Error calculating growth potential: {e}")
        return 10  # Default score
    
def calculate_efficiency_score(location_id, epc_data):
    """Calculate score based on energy efficiency (0-15)"""
    try:
        # Extract postcode district/area
        postcode_area = location_id
        if ' ' in location_id:
            postcode_area = location_id.split(' ')[0]
        
        # Filter for this location
        location_epc = epc_data[
            epc_data['postcode'].str.startswith(postcode_area, na=False)
        ]
        
        if len(location_epc) == 0:
            return 7.5  # Default score
        
        efficiency_score = 7.5  # Start in middle
        
        # Calculate average efficiency
        if 'current_energy_efficiency' in location_epc.columns:
            avg_efficiency = location_epc['current_energy_efficiency'].mean()
            
            # Higher efficiency = better score (0-7.5)
            # 50 is average, 80+ is excellent
            efficiency_component = min(avg_efficiency / 10, 7.5)
            efficiency_score = efficiency_component
        
        # Calculate improvement potential
        if 'efficiency_improvement' in location_epc.columns:
            avg_improvement = location_epc['efficiency_improvement'].mean()
            
            # Higher improvement potential = better investment (0-7.5)
            # 20 point improvement potential is good
            improvement_component = min(avg_improvement / 3, 7.5)
            efficiency_score += improvement_component
        
        return min(max(efficiency_score, 0), 15)
    
    except Exception as e:
        print(f"Error calculating efficiency score: {e}")
        return 7.5  # Default score