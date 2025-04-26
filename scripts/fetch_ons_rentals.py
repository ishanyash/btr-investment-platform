import os
import pandas as pd
import requests
from datetime import datetime

def fetch_ons_rental_data(output_dir='data/raw'):
    """
    Fetch ONS Private Rental Market Statistics
    
    Documentation: https://www.ons.gov.uk/peoplepopulationandcommunity/housing/datasets/privaterentalmarketsummarystatisticsinengland
    """
    # ONS API endpoint for private rental data
    # Using the HTTPS JSON API for ONS
    url = "https://api.ons.gov.uk/dataset/PRMS/timeseries"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Filename with date
    today = datetime.now().strftime('%Y%m%d')
    filename = f"{output_dir}/ons_rentals_{today}.csv"
    
    print(f"Fetching ONS rental statistics...")
    
    try:
        # Get available timeseries
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Initialize dataframe to store results
        all_data = []
        
        # Process each timeseries (rental data by region)
        for item in data.get('items', []):
            series_id = item.get('id')
            series_url = f"{url}/{series_id}/data"
            
            # Get the specific timeseries data
            series_response = requests.get(series_url)
            series_response.raise_for_status()
            series_data = series_response.json()
            
            # Extract data points
            for point in series_data.get('months', []):
                all_data.append({
                    'region': item.get('description'),
                    'date': point.get('date'),
                    'value': point.get('value'),
                    'unit': series_data.get('unit'),
                })
        
        # Convert to dataframe
        df = pd.DataFrame(all_data)
        
        # Save raw data
        df.to_csv(filename, index=False)
        
        # Create processed version with additional metrics
        processed_filename = filename.replace('raw', 'processed')
        
        # Add year-on-year growth calculation
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(['region', 'date'])
        df['prev_year'] = df.groupby('region')['value'].shift(12)
        df['yoy_growth'] = (df['value'] / df['prev_year'] - 1) * 100
        
        df.to_csv(processed_filename, index=False)
        
        print(f"Downloaded ONS rental data with {len(df)} records. Saved to {filename}")
        return df
        
    except Exception as e:
        print(f"Error downloading ONS rental data: {e}")
        return None

if __name__ == "__main__":
    fetch_ons_rental_data()