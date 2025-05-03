# src/__init__.py
# Empty file to make the directory a Python package

# src/components/__init__.py
# Import all component modules for easy access
from .data_dashboard import display_data_dashboard
from .mapping_util import display_btr_map
from .investment_calculator_page import display_investment_calculator

# src/utils/__init__.py
# Import utility functions for easy access
from .data_processor import (
    load_land_registry_data,
    load_ons_rental_data,
    load_planning_data,
    load_amenities_data,
    load_epc_data,
    postcode_to_area,
    calculate_investment_score,
    create_master_dataset
)