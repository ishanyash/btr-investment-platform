#!/usr/bin/env python3
import os
import sys
import logging
import argparse
from datetime import datetime

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

# Import data collection scripts
from scripts.fetch_land_registry import fetch_land_registry_data
from scripts.fetch_ons_rentals import fetch_ons_rental_data
from scripts.fetch_planning_applications import fetch_planning_applications
from scripts.fetch_osm_amenities import fetch_osm_amenities
from scripts.fetch_epc_ratings import fetch_epc_ratings

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
    
    # Create necessary directories
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    
    try:
        # Land Registry data
        logger.info("Collecting Land Registry data...")
        fetch_land_registry_data()
        
        # ONS rental data
        logger.info("Collecting ONS rental statistics...")
        fetch_ons_rental_data()
        
        # Planning applications
        logger.info("Collecting planning applications data...")
        fetch_planning_applications()
        
        # OSM amenities
        logger.info("Collecting OpenStreetMap amenities data...")
        fetch_osm_amenities()
        
        # EPC ratings
        logger.info("Collecting EPC ratings data...")
        epc_api_key = os.environ.get('EPC_API_KEY')
        if epc_api_key:
            logger.info("Using provided EPC API key")
        else:
            logger.info("No EPC API key found, using fallback bulk data method")
        fetch_epc_ratings(sample_size=10000)  # Limit sample size for regular runs
        
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