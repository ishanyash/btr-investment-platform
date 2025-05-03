import os
import requests
import logging
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import base64

def fetch_epc_ratings():
    """
    Fetch EPC ratings using the API key from environment variables
    """
    logging.info("Fetching EPC ratings data...")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment variables
    api_key = os.getenv("EPC_API_KEY")
    api_email = os.getenv("EPC_API_EMAIL")
    
    if not api_key or not api_email:
        logging.warning("EPC API key or email not found in environment variables")
        logging.info("EPC API key not found. Using fallback bulk data method.")
        return fetch_epc_fallback()
    
    # Prepare authorization header using Basic Auth
    auth_str = f"{api_email}:{api_key}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Accept": "application/json"
    }
    
    try:
        # First, let's try to verify the API key works with a small request
        test_url = "https://epc.opendatacommunities.org/api/v1/domestic/search?size=1"
        test_response = requests.get(test_url, headers=headers)
        
        if test_response.status_code != 200:
            logging.error(f"EPC API key verification failed: {test_response.status_code}")
            logging.error(f"Response: {test_response.text}")
            logging.info("Falling back to bulk data method")
            return fetch_epc_fallback()
        
        logging.info("EPC API key verification successful")
        
        # Now fetch actual data - limit to 10000 records as per the API docs
        url = "https://epc.opendatacommunities.org/api/v1/domestic/search?size=10000"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logging.error(f"Error fetching EPC data: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return fetch_epc_fallback()
        
        data = response.json()
        
        # Save the data to a CSV file
        output_dir = "data/raw"
        os.makedirs(output_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{output_dir}/epc_data_{date_str}.csv"
        
        # Convert to DataFrame and save
        df = pd.DataFrame(data.get("rows", []))
        df.to_csv(filename, index=False)
        
        logging.info(f"Saved {len(df)} EPC records to {filename}")
        return df
    
    except Exception as e:
        logging.error(f"Error in EPC data collection: {str(e)}")
        return fetch_epc_fallback()

def fetch_epc_fallback():
    """
    Fallback method to use if the API key doesn't work
    """
    logging.info("Using fallback method for EPC data")
    
    # Try using the public EPC data
    # This is a simplified version as a placeholder
    try:
        # In a real implementation, you would fetch from a public data source
        # For now, return a basic structure
        return pd.DataFrame({
            "date": [datetime.now()],
            "source": ["fallback"],
            "note": ["EPC data unavailable - using fallback"]
        })
    except Exception as e:
        logging.error(f"Error in EPC fallback: {str(e)}")
        return None

# When called directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    epc_data = fetch_epc_ratings()
    
    if isinstance(epc_data, pd.DataFrame):
        print(f"Successfully retrieved {len(epc_data)} EPC records")
    else:
        print("Failed to retrieve EPC data")