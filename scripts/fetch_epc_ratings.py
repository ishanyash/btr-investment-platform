import os
import pandas as pd
import requests
import zipfile
from io import BytesIO
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger('btr_data_collection.epc')

def fetch_epc_ratings(output_dir='data/raw', sample_size=None):
    """
    Fetch EPC (Energy Performance Certificate) data from the UK government
    
    Args:
        output_dir: Directory to save the output
        sample_size: Optional limit on number of records to process
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    processed_dir = output_dir.replace('raw', 'processed')
    os.makedirs(processed_dir, exist_ok=True)
    
    # Filename with date
    today = datetime.now().strftime('%Y%m%d')
    filename = f"{output_dir}/epc_ratings_{today}.csv"
    processed_filename = f"{processed_dir}/epc_ratings_{today}.csv"
    
    logger.info("Fetching EPC ratings data...")
    
    try:
        # Get API key from environment variable (set by GitHub Actions)
        api_key = os.environ.get('EPC_API_KEY')
        
        if not api_key:
            logger.info("EPC API key not found. Using fallback bulk data method.")
            
            # This is the publicly available bulk data
            current_year = datetime.now().year
            current_quarter = (datetime.now().month - 1) // 3 + 1
            bulk_url = f"https://epc.opendatacommunities.org/api/v1/domestic/search?size=10000"
            
            logger.info(f"Downloading bulk EPC data from {bulk_url}")
            response = requests.get(bulk_url, stream=True)
            response.raise_for_status()
            
            # Process the zip file
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                # Get the first CSV in the zip
                csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                if not csv_files:
                    raise Exception("No CSV files found in the ZIP archive")
                
                logger.info(f"Found {len(csv_files)} CSV files in the archive")
                logger.info(f"Processing {csv_files[0]}")
                
                # Extract the first CSV file
                with z.open(csv_files[0]) as f:
                    df = pd.read_csv(f)
                    
                    # Limit sample size if specified
                    if sample_size and len(df) > sample_size:
                        logger.info(f"Limiting to {sample_size} random samples from {len(df)} records")
                        df = df.sample(sample_size, random_state=42)
                    
                    # Save raw data
                    df.to_csv(filename, index=False)
                    logger.info(f"Saved raw data to {filename}")
        else:
            # Use the API with authentication
            logger.info("Using EPC API with provided key")
            url = "https://epc.opendatacommunities.org/api/v1/domestic/search"
            
            headers = {
                "Accept": "application/json",
                "Authorization": f"Basic {api_key}"
            }
            
            # Parameters for the search
            params = {
                "size": sample_size if sample_size else 1000,  # API limit is 10,000
                "from": 0
            }
            
            logger.info(f"Querying EPC API with size={params['size']}")
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data['rows'])
            df.to_csv(filename, index=False)
            logger.info(f"Saved {len(df)} records from API to {filename}")
        
        # Create processed version with useful metrics
        try:
            logger.info("Processing EPC data...")
            # Try to standardize column names based on the source
            if 'current-energy-rating' in df.columns:
                # API data format
                cols_to_extract = [
                    'postcode', 'address1', 'address2', 'address3',
                    'current-energy-rating', 'potential-energy-rating',
                    'current-energy-efficiency', 'potential-energy-efficiency',
                    'property-type', 'built-form', 'construction-age-band',
                    'total-floor-area'
                ]
                
                # Only select columns that actually exist
                cols_to_extract = [col for col in cols_to_extract if col in df.columns]
                df_processed = df[cols_to_extract]
                
                # Rename columns for consistency
                column_mapping = {
                    'current-energy-rating': 'current_energy_rating',
                    'potential-energy-rating': 'potential_energy_rating',
                    'current-energy-efficiency': 'current_energy_efficiency',
                    'potential-energy-efficiency': 'potential_energy_efficiency',
                    'property-type': 'property_type',
                    'built-form': 'built_form',
                    'construction-age-band': 'construction_age_band',
                    'total-floor-area': 'total_floor_area'
                }
                
                df_processed = df_processed.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
                
            else:
                # Bulk data format - adjust column selection based on actual data
                # This is an attempt to map common column names in the bulk data
                possible_cols = {
                    'POSTCODE': 'postcode',
                    'POST_CODE': 'postcode',
                    'BUILDING_REFERENCE_NUMBER': 'building_reference_number',
                    'ADDRESS1': 'address1',
                    'ADDRESS_1': 'address1',
                    'ADDRESS2': 'address2',
                    'ADDRESS_2': 'address2',
                    'ADDRESS3': 'address3',
                    'ADDRESS_3': 'address3',
                    'CURRENT_ENERGY_RATING': 'current_energy_rating',
                    'ENERGY_RATING_CURRENT': 'current_energy_rating',
                    'CURRENT_EPC_RATING': 'current_energy_rating',
                    'POTENTIAL_ENERGY_RATING': 'potential_energy_rating',
                    'ENERGY_RATING_POTENTIAL': 'potential_energy_rating',
                    'POTENTIAL_EPC_RATING': 'potential_energy_rating',
                    'CURRENT_ENERGY_EFFICIENCY': 'current_energy_efficiency',
                    'ENERGY_EFFICIENCY_CURRENT': 'current_energy_efficiency',
                    'POTENTIAL_ENERGY_EFFICIENCY': 'potential_energy_efficiency',
                    'ENERGY_EFFICIENCY_POTENTIAL': 'potential_energy_efficiency',
                    'PROPERTY_TYPE': 'property_type',
                    'BUILT_FORM': 'built_form',
                    'CONSTRUCTION_AGE_BAND': 'construction_age_band',
                    'CONSTRUCTION_YEAR': 'construction_year',
                    'TOTAL_FLOOR_AREA': 'total_floor_area',
                    'FLOOR_AREA': 'total_floor_area'
                }
                
                # Map columns that exist in the dataframe
                col_mapping = {old: new for old, new in possible_cols.items() if old in df.columns}
                
                if col_mapping:
                    df_processed = df.rename(columns=col_mapping)
                    # Select only the mapped columns
                    df_processed = df_processed[[v for v in col_mapping.values()]]
                else:
                    # If we can't identify the right columns, just use all columns
                    df_processed = df.copy()
                    # Convert column names to lowercase with underscores
                    df_processed.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df_processed.columns]
            
            # Calculate improvement potential (if the columns exist)
            efficiency_cols = ['current_energy_efficiency', 'potential_energy_efficiency']
            if all(col in df_processed.columns for col in efficiency_cols):
                df_processed['efficiency_improvement'] = (
                    df_processed['potential_energy_efficiency'] - df_processed['current_energy_efficiency']
                )
                logger.info("Calculated efficiency improvement potential")
            
            # Create EPC numeric score
            rating_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7}
            if 'current_energy_rating' in df_processed.columns:
                if df_processed['current_energy_rating'].dtype == 'object':
                    # Check if values are in the expected format
                    if df_processed['current_energy_rating'].str.match('^[A-G]$').any():
                        df_processed['current_rating_score'] = df_processed['current_energy_rating'].map(rating_map)
                        logger.info("Added numeric rating scores")
            
            # Add investment opportunity score (simple version)
            # Properties with poor ratings (E, F, G) but high improvement potential are good targets
            if 'current_energy_rating' in df_processed.columns and 'efficiency_improvement' in df_processed.columns:
                # Create a normalized improvement score (0-100)
                max_improvement = df_processed['efficiency_improvement'].max()
                if max_improvement > 0:
                    df_processed['improvement_score'] = (df_processed['efficiency_improvement'] / max_improvement) * 100
                
                # Weight poor rated properties higher
                if 'current_rating_score' in df_processed.columns:
                    # Invert rating (so G=7 becomes score of 7/7=1.0 and A=1 becomes 1/7=0.14)
                    df_processed['rating_weight'] = df_processed['current_rating_score'] / 7.0
                    
                    # Calculate EPC investment opportunity score (0-100)
                    if 'improvement_score' in df_processed.columns:
                        df_processed['epc_opportunity_score'] = (
                            df_processed['improvement_score'] * 0.6 + 
                            df_processed['rating_weight'] * 40  # Scale to 0-40 for rating weight
                        )
                        logger.info("Calculated EPC investment opportunity scores")
            
            # Save processed data
            df_processed.to_csv(processed_filename, index=False)
            logger.info(f"Saved processed EPC data to {processed_filename} with {len(df_processed)} records")
            
            return df_processed
            
        except Exception as e:
            logger.error(f"Error processing EPC data: {e}", exc_info=True)
            # Save the raw data anyway
            df.to_csv(processed_filename, index=False)
            logger.info(f"Saved raw data as processed due to processing error")
            return df
            
    except Exception as e:
        logger.error(f"Error fetching EPC data: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    # Set up console logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Run the function
    sample_size = 5000  # Limit to 5000 records for testing
    fetch_epc_ratings(sample_size=sample_size)
