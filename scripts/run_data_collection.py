#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

# Import data collection scripts
from fetch_land_registry import fetch_land_registry_data
from fetch_ons_rentals import fetch_ons_rental_data  # Updated import
from fetch_planning_applications import fetch_planning_applications  # Updated import
from fetch_osm_amenities import fetch_osm_amenities
from fetch_epc_ratings import fetch_epc_ratings  # Updated import

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(project_root, 'data_collection.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('btr_data_collection')

def collect_all_data():
    """Collect data from all sources"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"Starting data collection at {timestamp}")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Create necessary directories
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    
    try:
        # Land Registry data
        logger.info("Collecting Land Registry data...")
        fetch_land_registry_data()
        
        # ONS rental data
        logger.info("Collecting ONS rental statistics...")
        rental_data = fetch_ons_rental_data()
        if rental_data:
            logger.info(f"Successfully collected {len(rental_data)} ONS rental datasets")
            # Process the rental data further if needed
            for dataset in rental_data:
                logger.info(f"Retrieved dataset: {dataset.get('title')} saved to {dataset.get('filename')}")
        else:
            logger.warning("Failed to collect ONS rental data")
        
        # Planning applications
        logger.info("Collecting planning applications data...")
        planning_data = fetch_planning_applications()
        if isinstance(planning_data, pd.DataFrame) and not planning_data.empty:
            logger.info(f"Successfully collected {len(planning_data)} planning applications")
        else:
            logger.warning("No planning applications found or errors occurred")
        
        # OSM amenities
        logger.info("Collecting OpenStreetMap amenities data...")
        fetch_osm_amenities()
        
        # EPC ratings
        logger.info("Collecting EPC ratings data...")
        epc_api_key = os.environ.get('EPC_API_KEY')
        epc_api_email = os.environ.get('EPC_API_EMAIL')
        
        if epc_api_key and epc_api_email:
            logger.info("Using provided EPC API credentials")
        else:
            logger.info("No EPC API credentials found, using fallback bulk data method")
        
        epc_data = fetch_epc_ratings()
        if isinstance(epc_data, pd.DataFrame) and not epc_data.empty:
            logger.info(f"Successfully collected {len(epc_data)} EPC records")
        else:
            logger.warning("Failed to collect EPC data or using fallback data")
        
        logger.info("Data collection completed successfully")
        
    except Exception as e:
        logger.error(f"Error during data collection: {e}", exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(description='BTR Data Collection Tool')
    parser.add_argument('--run-now', action='store_true', help='Run data collection immediately')
    args = parser.parse_args()
    
    if args.run_now:
        logger.info("Running data collection immediately...")
        collect_all_data()
    else:
        logger.info("No action specified. Use --run-now to collect data.")

if __name__ == "__main__":
    main()