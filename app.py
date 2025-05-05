import streamlit as st
import os
import sys

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

# Import only what's needed for report generation
from src.components.btr_report_generator import display_btr_report_generator

st.set_page_config(
    page_title="BTR Investment Report Generator",
    page_icon="🏘️",
    layout="wide"
)

def main():
    # Direct focus on the report generator
    display_btr_report_generator()

if __name__ == "__main__":
    main()
