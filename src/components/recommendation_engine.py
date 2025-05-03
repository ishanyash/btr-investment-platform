import pandas as pd
import numpy as np
from .location_score_algorithm import calculate_location_score
from ..utils.data_processor import (
    load_land_registry_data,
    load_ons_rental_data,
    load_planning_data,
    load_amenities_data,
    load_epc_data
)

class BTRRecommendationEngine:
    """
    Recommendation engine for BTR investment opportunities
    """
    
    def __init__(self):
        """Initialize the recommendation engine with data"""
        self.land_registry_data = load_land_registry_data()
        self.rental_data = load_ons_rental_data()
        self.planning_data = load_planning_data()
        self.amenities_data = load_amenities_data()
        self.epc_data = load_epc_data()
        
        # Investment strategies
        self.strategies = {
            'yield_maximizer': {
                'description': 'Maximize rental yield',
                'weights': {
                    'location_score': 0.3,
                    'rental_yield': 0.4,
                    'affordability': 0.2,
                    'growth_potential': 0.1
                }
            },
            'capital_growth': {
                'description': 'Focus on capital appreciation',
                'weights': {
                    'location_score': 0.3,
                    'rental_yield': 0.1,
                    'affordability': 0.2,
                    'growth_potential': 0.4
                }
            },
            'balanced': {
                'description': 'Balanced approach (yield and growth)',
                'weights': {
                    'location_score': 0.3,
                    'rental_yield': 0.25,
                    'affordability': 0.2,
                    'growth_potential': 0.25
                }
            },
            'value_add': {
                'description': 'Properties with renovation/conversion potential',
                'weights': {
                    'location_score': 0.3,
                    'rental_yield': 0.15,
                    'affordability': 0.2,
                    'growth_potential': 0.15,
                    'improvement_potential': 0.2
                }
            },
            'sfh_focused': {
                'description': 'Focus on Single Family Housing opportunities',
                'weights': {
                    'location_score': 0.3,
                    'rental_yield': 0.25,
                    'affordability': 0.2,
                    'growth_potential': 0.15,
                    'sfh_suitability': 0.1
                }
            }
        }
    
    def recommend_locations(self, strategy='balanced', top_n=5):
        """
        Recommend top locations based on the selected strategy
        
        Parameters:
        -----------
        strategy : str
            Investment strategy key
        top_n : int
            Number of top recommendations to return
            
        Returns:
        --------
        list
            List of top recommended locations with scores
        """
        if strategy not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Get strategy weights
        weights = self.strategies[strategy]['weights']
        
        # Get locations to evaluate
        locations = self._get_locations()
        
        # Calculate scores for each location
        scored_locations = []
        
        for location in locations:
            # Calculate base location score
            location_result = calculate_location_score(
                location,
                amenities_data=self.amenities_data,
                rental_data=self.rental_data,
                epc_data=self.epc_data,
                land_registry_data=self.land_registry_data,
                planning_data=self.planning_data
            )
            
            # Calculate other metrics based on strategy
            metrics = {
                'location_score': location_result['overall_score'] / 100,  # Normalize to 0-1
                'rental_yield': self._calculate_rental_yield(location),
                'affordability': self._calculate_affordability(location),
                'growth_potential': self._calculate_growth_potential(location),
            }
            
            # Add strategy-specific metrics
            if 'improvement_potential' in weights:
                metrics['improvement_potential'] = self._calculate_improvement_potential(location)
            
            if 'sfh_suitability' in weights:
                metrics['sfh_suitability'] = self._calculate_sfh_suitability(location)
            
            # Calculate weighted score
            total_score = 0
            for metric, weight in weights.items():
                if metric in metrics:
                    total_score += metrics[metric] * weight
            
            # Add to results
            scored_locations.append({
                'location': location,
                'overall_score': total_score * 100,  # Scale to 0-100
                'location_score': location_result['overall_score'],
                'metrics': metrics
            })
        
        # Sort by overall score
        sorted_locations = sorted(scored_locations, key=lambda x: x['overall_score'], reverse=True)
        
        # Return top N
        return sorted_locations[:top_n]
    
    def recommend_properties(self, budget, strategy='balanced', top_n=5):
        """
        Recommend specific properties based on budget and strategy
        
        Parameters:
        -----------
        budget : float
            Maximum budget for property acquisition
        strategy : str
            Investment strategy key
        top_n : int
            Number of top recommendations to return
            
        Returns:
        --------
        list
            List of top recommended properties with scores
        """
        if strategy not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Filter Land Registry data by price
        if self.land_registry_data is None:
            return []
        
        filtered_properties = self.land_registry_data[self.land_registry_data['price'] <= budget]
        
        if len(filtered_properties) == 0:
            return []
        
        # Sample properties for scoring (to limit processing)
        sample_size = min(100, len(filtered_properties))
        sampled_properties = filtered_properties.sample(sample_size)
        
        # Score each property
        scored_properties = []
        
        for _, property_row in sampled_properties.iterrows():
            # Extract property details
            property_info = {
                'price': property_row['price'],
                'postcode': property_row['postcode'],
                'property_type': property_row['property_type'],
                'tenure_type': property_row['tenure_type'] if 'tenure_type' in property_row else None,
                'district': property_row['district'] if 'district' in property_row else None,
            }
            
            # Get location from postcode
            location = property_info['postcode'].split(' ')[0] if property_info['postcode'] else property_info['district']
            
            # Calculate location score
            location_result = calculate_location_score(
                location,
                amenities_data=self.amenities_data,
                rental_data=self.rental_data,
                epc_data=self.epc_data,
                land_registry_data=self.land_registry_data,
                planning_data=self.planning_data
            )
            
            # Calculate property-specific metrics
            property_metrics = {
                'location_score': location_result['overall_score'] / 100,
                'rental_yield': self._estimate_property_yield(property_info),
                'affordability': self._calculate_property_affordability(property_info),
                'growth_potential': self._calculate_property_growth(property_info, location),
            }
            
            # Add strategy-specific metrics
            weights = self.strategies[strategy]['weights']
            
            if 'improvement_potential' in weights:
                property_metrics['improvement_potential'] = self._calculate_property_improvement_potential(property_info)
            
            if 'sfh_suitability' in weights:
                property_metrics['sfh_suitability'] = self._calculate_property_sfh_suitability(property_info)
            
            # Calculate weighted score
            total_score = 0
            for metric, weight in weights.items():
                if metric in property_metrics:
                    total_score += property_metrics[metric] * weight
            
            # Add to results
            scored_properties.append({
                'property': property_info,
                'location': location,
                'overall_score': total_score * 100,  # Scale to 0-100
                'location_score': location_result['overall_score'],
                'metrics': property_metrics
            })
        
        # Sort by overall score
        sorted_properties = sorted(scored_properties, key=lambda x: x['overall_score'], reverse=True)
        
        # Return top N
        return sorted_properties[:top_n]
    
    def _get_locations(self):
        """Get list of locations to evaluate"""
        locations = set()
        
        # Add major cities
        major_cities = [
            'London', 'Manchester', 'Birmingham', 'Leeds', 'Glasgow',
            'Liverpool', 'Bristol', 'Sheffield', 'Edinburgh', 'Cardiff'
        ]
        locations.update(major_cities)
        
        # Add from amenities data
        if self.amenities_data is not None and 'location' in self.amenities_data.columns:
            locations.update(self.amenities_data['location'].unique())
        
        # Add from land registry (postcode districts)
        if self.land_registry_data is not None and 'postcode' in self.land_registry_data.columns:
            # Extract postcode districts (first part of postcode)
            districts = self.land_registry_data['postcode'].apply(
                lambda x: x.split(' ')[0] if isinstance(x, str) and ' ' in x else None
            )
            locations.update([d for d in districts.unique() if d])
        
        return list(locations)
    
    def _calculate_rental_yield(self, location):
        """Calculate rental yield score for a location (0-1)"""
        try:
            # Default yield if no data
            default_yield = 0.5
            
            if self.rental_data is None:
                return default_yield
            
            # Find rental data for this location
            if 'region' in self.rental_data.columns:
                location_data = self.rental_data[self.rental_data['region'].str.contains(location, case=False, na=False)]
                
                if len(location_data) > 0 and 'value' in location_data.columns:
                    avg_rent = location_data['value'].mean()
                    
                    # Find property prices for this location
                    if self.land_registry_data is not None and 'postcode' in self.land_registry_data.columns:
                        location_properties = self.land_registry_data[
                            self.land_registry_data['postcode'].str.startswith(location, na=False)
                        ]
                        
                        if len(location_properties) > 0:
                            avg_price = location_properties['price'].mean()
                            
                            if avg_price > 0:
                                # Calculate annual yield
                                annual_rent = avg_rent * 12
                                yield_value = annual_rent / avg_price
                                
                                # Normalize to 0-1 (typically 3-7% is normal range)
                                normalized_yield = min(max((yield_value - 0.03) / 0.04, 0), 1)
                                return normalized_yield
            
            return default_yield
            
        except Exception as e:
            print(f"Error calculating rental yield for {location}: {e}")
            return 0.5  # Default middle value
    
    def _calculate_affordability(self, location):
        """Calculate affordability score for a location (0-1)"""
        try:
            if self.land_registry_data is None:
                return 0.5  # Default middle value
            
            # Get property prices for this location
            location_properties = self.land_registry_data[
                self.land_registry_data['postcode'].str.startswith(location, na=False)
            ]
            
            if len(location_properties) > 0:
                avg_price = location_properties['price'].mean()
                
                # Get national average
                national_avg = self.land_registry_data['price'].mean()
                
                if national_avg > 0:
                    # Calculate price ratio to national average
                    price_ratio = avg_price / national_avg
                    
                    # Normalize to 0-1 (lower is more affordable)
                    # We want 0.8x to 1.2x of national average to be around 0.5
                    if price_ratio < 0.8:
                        # More affordable than average (higher score)
                        return min(1.0, 0.5 + (0.8 - price_ratio) / 0.6)
                    else:
                        # Less affordable than average (lower score)
                        return max(0.0, 0.5 - (price_ratio - 0.8) / 2.4)
            
            return 0.5  # Default middle value
            
        except Exception as e:
            print(f"Error calculating affordability for {location}: {e}")
            return 0.5
    
    def _calculate_growth_potential(self, location):
        """Calculate growth potential score for a location (0-1)"""
        try:
            # Default if no data
            default_growth = 0.5
            
            # Check planning applications (new developments indicate growth)
            if self.planning_data is not None:
                # Planning data would need address or location field
                # This is a placeholder for the actual implementation
                pass
            
            # Check historic price growth from Land Registry
            if self.land_registry_data is not None and 'date_of_transfer' in self.land_registry_data.columns:
                # Filter for this location
                location_sales = self.land_registry_data[
                    self.land_registry_data['postcode'].str.startswith(location, na=False)
                ]
                
                if len(location_sales) > 10:  # Need sufficient data
                    # Convert dates to datetime
                    location_sales['date_of_transfer'] = pd.to_datetime(location_sales['date_of_transfer'])
                    
                    # Group by year and calculate average price
                    location_sales['year'] = location_sales['date_of_transfer'].dt.year
                    yearly_prices = location_sales.groupby('year')['price'].mean()
                    
                    if len(yearly_prices) > 1:
                        # Calculate annual growth rate
                        years = sorted(yearly_prices.index)
                        first_year = years[0]
                        last_year = years[-1]
                        
                        if last_year > first_year:
                            first_price = yearly_prices[first_year]
                            last_price = yearly_prices[last_year]
                            
                            if first_price > 0:
                                # Compound annual growth rate
                                years_diff = last_year - first_year
                                annual_growth = (last_price / first_price) ** (1 / years_diff) - 1
                                
                                # Normalize to 0-1 (typically 0-10% annual growth)
                                normalized_growth = min(max(annual_growth / 0.1, 0), 1)
                                return normalized_growth
            
            return default_growth
            
        except Exception as e:
            print(f"Error calculating growth potential for {location}: {e}")
            return 0.5
    
    def _calculate_improvement_potential(self, location):
        """Calculate property improvement potential score for a location (0-1)"""
        try:
            if self.epc_data is None:
                return 0.5  # Default middle value
            
            # Filter EPC data for this location
            location_epc = self.epc_data[
                self.epc_data['postcode'].str.startswith(location, na=False)
            ]
            
            if len(location_epc) > 0:
                # Check if we have efficiency columns
                if 'current_energy_efficiency' in location_epc.columns and 'potential_energy_efficiency' in location_epc.columns:
                    # Calculate average improvement potential
                    current_avg = location_epc['current_energy_efficiency'].mean()
                    potential_avg = location_epc['potential_energy_efficiency'].mean()
                    
                    improvement = potential_avg - current_avg
                    
                    # Normalize to 0-1 (typically 0-30 points improvement)
                    normalized_improvement = min(max(improvement / 30, 0), 1)
                    return normalized_improvement
                
                # Check if we have rating columns
                elif 'current_energy_rating' in location_epc.columns:
                    # Count properties with poor ratings (high improvement potential)
                    poor_ratings = location_epc['current_energy_rating'].isin(['E', 'F', 'G']).mean()
                    
                    # More poor ratings = higher improvement potential
                    return poor_ratings
            
            return 0.5  # Default middle value
            
        except Exception as e:
            print(f"Error calculating improvement potential for {location}: {e}")
            return 0.5
    
    def _calculate_sfh_suitability(self, location):
        """Calculate single family housing suitability score for a location (0-1)"""
        try:
            if self.land_registry_data is None:
                return 0.5  # Default middle value
            
            # Filter for this location
            location_properties = self.land_registry_data[
                self.land_registry_data['postcode'].str.startswith(location, na=False)
            ]
            
            if len(location_properties) > 0 and 'property_type' in location_properties.columns:
                # Calculate percentage of houses vs flats
                house_types = ['D', 'S', 'T']  # Detached, Semi-detached, Terraced
                
                houses = location_properties['property_type'].isin(house_types).sum()
                total = len(location_properties)
                
                if total > 0:
                    house_ratio = houses / total
                    
                    # Areas with 50-80% houses are ideal for SFH (not too many flats, but not all houses)
                    if house_ratio >= 0.5 and house_ratio <= 0.8:
                        return 1.0
                    elif house_ratio > 0.8:
                        # Too many houses might mean market saturation
                        return 0.7
                    else:
                        # Less than 50% houses might mean it's more of a flat/apartment area
                        return max(0.3, house_ratio)
            
            return 0.5  # Default middle value
            
        except Exception as e:
            print(f"Error calculating SFH suitability for {location}: {e}")
            return 0.5
    
    def _estimate_property_yield(self, property_info):
        """Estimate rental yield for a specific property (0-1)"""
        try:
            if 'postcode' not in property_info or self.rental_data is None:
                return 0.5  # Default middle value
            
            # Extract postcode area
            postcode = property_info['postcode']
            postcode_area = postcode.split(' ')[0] if ' ' in postcode else postcode
            
            # Get average rent for this area
            area_data = self.rental_data
            if 'region' in self.rental_data.columns:
                area_data = self.rental_data[self.rental_data['region'].str.contains(postcode_area, case=False, na=False)]
            
            if len(area_data) > 0 and 'value' in area_data.columns:
                avg_rent = area_data['value'].mean()
            else:
                # Use national average as fallback
                avg_rent = self.rental_data['value'].mean() if 'value' in self.rental_data.columns else 1000
            
            # Adjust rent based on property type
            property_type = property_info.get('property_type', 'F')  # Default to flat if unknown
            
            # Property type adjustments
            type_multipliers = {
                'D': 1.4,  # Detached
                'S': 1.2,  # Semi-detached
                'T': 1.0,  # Terraced
                'F': 0.9   # Flat
            }
            
            multiplier = type_multipliers.get(property_type, 1.0)
            property_rent = avg_rent * multiplier
            
            # Calculate annual yield
            annual_rent = property_rent * 12
            price = property_info['price']
            
            if price > 0:
                yield_value = annual_rent / price
                
                # Normalize to 0-1 (typically 3-7% is normal range)
                normalized_yield = min(max((yield_value - 0.03) / 0.04, 0), 1)
                return normalized_yield
            
            return 0.5  # Default middle value
            
        except Exception as e:
            print(f"Error estimating property yield: {e}")
            return 0.5
    
    def _calculate_property_affordability(self, property_info):
        """Calculate affordability score for a specific property (0-1)"""
        try:
            if 'price' not in property_info or self.land_registry_data is None:
                return 0.5
            
            price = property_info['price']
            
            # Get national average price
            national_avg = self.land_registry_data['price'].mean()
            
            if national_avg > 0:
                # Calculate price ratio
                price_ratio = price / national_avg
                
                # Normalize to 0-1 (lower is more affordable)
                if price_ratio < 0.8:
                    # More affordable than average (higher score)
                    return min(1.0, 0.5 + (0.8 - price_ratio) / 0.6)
                else:
                    # Less affordable than average (lower score)
                    return max(0.0, 0.5 - (price_ratio - 0.8) / 2.4)
            
            return 0.5
            
        except Exception as e:
            print(f"Error calculating property affordability: {e}")
            return 0.5
    
    def _calculate_property_growth(self, property_info, location):
        """Calculate growth potential for a specific property (0-1)"""
        # For individual properties, we rely more on location growth
        return self._calculate_growth_potential(location)
    
    def _calculate_property_improvement_potential(self, property_info):
        """Calculate improvement potential for a specific property (0-1)"""
        try:
            if 'postcode' not in property_info or self.epc_data is None:
                return 0.5
            
            postcode = property_info['postcode']
            
            # Try to find this exact property in EPC data
            property_epc = self.epc_data[
                self.epc_data['postcode'] == postcode
            ]
            
            if len(property_epc) > 0:
                # Use actual EPC data for this property
                if 'current_energy_efficiency' in property_epc.columns and 'potential_energy_efficiency' in property_epc.columns:
                    current = property_epc['current_energy_efficiency'].iloc[0]
                    potential = property_epc['potential_energy_efficiency'].iloc[0]
                    
                    improvement = potential - current
                    
                    # Normalize to 0-1 (typically 0-30 points improvement)
                    normalized_improvement = min(max(improvement / 30, 0), 1)
                    return normalized_improvement
                
                elif 'current_energy_rating' in property_epc.columns:
                    # Map ratings to scores
                    rating = property_epc['current_energy_rating'].iloc[0]
                    rating_scores = {
                        'A': 0.1,  # Already good, little improvement needed
                        'B': 0.2,
                        'C': 0.4,
                        'D': 0.6,
                        'E': 0.8,
                        'F': 0.9,
                        'G': 1.0   # Worst rating, highest improvement potential
                    }
                    
                    return rating_scores.get(rating, 0.5)
            
            # Fallback to age-based estimate if property type available
            property_type = property_info.get('property_type')
            
            if property_type:
                # Older properties typically have more improvement potential
                if property_type in ['D', 'S', 'T']:  # Houses
                    return 0.7  # Higher improvement potential for houses
                else:
                    return 0.5  # Average for flats
            
            return 0.5
            
        except Exception as e:
            print(f"Error calculating property improvement potential: {e}")
            return 0.5
    
    def _calculate_property_sfh_suitability(self, property_info):
        """Calculate SFH suitability for a specific property (0-1)"""
        try:
            if 'property_type' not in property_info:
                return 0.5
            
            property_type = property_info['property_type']
            
            # Direct mapping based on property type
            if property_type == 'D':  # Detached
                return 1.0
            elif property_type == 'S':  # Semi-detached
                return 0.9
            elif property_type == 'T':  # Terraced
                return 0.7
            elif property_type == 'F':  # Flat
                return 0.2
            else:
                return 0.5
                
        except Exception as e:
            print(f"Error calculating property SFH suitability: {e}")
            return 0.5