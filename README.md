# BTR Investment Platform

A data-driven platform for analyzing Buy-to-Rent investment opportunities across the UK using free, open-source tools.

## Overview

This platform integrates data from multiple sources to provide comprehensive insights for BTR investments, helping identify top UK rental opportunities with zero subscription costs.

## Features

- **Data Integration**: Combines data from Land Registry, ONS, Planning Portal, OpenStreetMap, and EPC ratings
- **Location Analysis**: Scores locations based on multiple factors including amenities and rental potential
- **Investment Calculator**: Calculates potential returns including purchase costs, refurbishment, and rental yield
- **Risk Assessment**: Evaluates investment risks based on market data and property characteristics

## Project Structure

btr-investment-platform/
├── data/                      # Data storage
│   ├── raw/                   # Raw data files
│   └── processed/             # Processed data files
├── scripts/                   # Data collection scripts
│   ├── fetch_land_registry.py
│   ├── fetch_ons_rentals.py
│   ├── fetch_planning_applications.py
│   ├── fetch_osm_amenities.py
│   ├── fetch_epc_ratings.py
│   └── run_data_collection.py # Main data collection script
├── src/                       # Source code
│   ├── app.py                 # Main Streamlit app
│   ├── components/            # UI components
│   ├── pages/                 # App pages
│   └── utils/                 # Utility functions
├── tests/                     # Unit tests
├── .env                       # Environment variables
├── .gitignore                 # Git ignore file
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Docker Compose configuration
├── README.md                  # This README
└── requirements.txt           # Python dependencies
