import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(project_root)

from src.components.recommendation_engine import BTRRecommendationEngine

def display_recommendations():
    """Display the BTR investment recommendations page"""
    st.title("BTR Investment Recommendations")
    st.write("""
    Get personalized Buy-to-Rent investment recommendations based on your investment strategy and budget.
    Our recommendation engine analyzes multiple data sources to find the best opportunities.
    """)
    
    # Initialize recommendation engine
    recommendation_engine = BTRRecommendationEngine()
    
    # Create tabs for different recommendation types
    tab1, tab2 = st.tabs(["Location Recommendations", "Property Recommendations"])
    
    with tab1:
        display_location_recommendations(recommendation_engine)
    
    with tab2:
        display_property_recommendations(recommendation_engine)


def display_location_recommendations(engine):
    """Display location-based recommendations"""
    st.header("Top BTR Location Recommendations")
    st.write("Discover the best areas for BTR investment based on your strategy.")
    
    # Strategy selection
    st.subheader("Investment Strategy")
    strategy = st.selectbox(
        "Select your investment strategy",
        list(engine.strategies.keys()),
        format_func=lambda x: engine.strategies[x]['description']
    )
    
    # Number of recommendations
    num_recommendations = st.slider("Number of recommendations", 3, 10, 5)
    
    # Get recommendations button
    if st.button("Get Location Recommendations"):
        with st.spinner("Analyzing locations..."):
            try:
                # Get recommendations
                recommendations = engine.recommend_locations(
                    strategy=strategy,
                    top_n=num_recommendations
                )
                
                if recommendations:
                    st.success(f"Found {len(recommendations)} recommended locations")
                    
                    # Create map of recommended locations
                    display_recommendation_map(recommendations)
                    
                    # Display table of recommendations
                    display_location_table(recommendations, strategy, engine.strategies[strategy]['weights'])
                    
                    # Display comparison chart
                    display_location_comparison_chart(recommendations)
                else:
                    st.warning("No locations found matching your criteria. Try adjusting your strategy.")
            except Exception as e:
                st.error(f"Error generating recommendations: {str(e)}")
    else:
        st.info("Click the button above to generate location recommendations.")


def display_property_recommendations(engine):
    """Display property-based recommendations"""
    st.header("Top BTR Property Recommendations")
    st.write("Find specific properties that match your investment criteria.")
    
    # Budget selection
    st.subheader("Investment Budget")
    budget = st.slider("Maximum budget (£)", 100000, 1000000, 350000, 50000)
    
    # Strategy selection
    st.subheader("Investment Strategy")
    strategy = st.selectbox(
        "Select your investment strategy",
        list(engine.strategies.keys()),
        format_func=lambda x: engine.strategies[x]['description'],
        key="property_strategy"
    )
    
    # Number of recommendations
    num_recommendations = st.slider("Number of recommendations", 3, 10, 5, key="property_num")
    
    # Get recommendations button
    if st.button("Get Property Recommendations"):
        with st.spinner("Analyzing properties..."):
            try:
                # Get recommendations
                recommendations = engine.recommend_properties(
                    budget=budget,
                    strategy=strategy,
                    top_n=num_recommendations
                )
                
                if recommendations:
                    st.success(f"Found {len(recommendations)} recommended properties within your budget")
                    
                    # Display table of recommendations
                    display_property_table(recommendations, strategy, engine.strategies[strategy]['weights'])
                    
                    # Display comparison chart
                    display_property_comparison_chart(recommendations)
                else:
                    st.warning("No properties found matching your criteria. Try adjusting your budget or strategy.")
            except Exception as e:
                st.error(f"Error generating recommendations: {str(e)}")
    else:
        st.info("Click the button above to generate property recommendations.")


def display_recommendation_map(recommendations):
    """Display a map of recommended locations"""
    import folium
    from folium.plugins import MarkerCluster
    import streamlit.components.v1 as components
    
    # Create base map centered on UK
    uk_center = [54.7, -4.2]
    m = folium.Map(location=uk_center, zoom_start=6, tiles="CartoDB positron")
    
    # Create marker cluster
    marker_cluster = MarkerCluster().add_to(m)
    
    # Add markers for each location
    for rec in recommendations:
        # Skip if no coordinates
        if 'lat' not in rec and 'lon' not in rec:
            continue
            
        # Default coordinates if missing
        lat = rec.get('lat', uk_center[0])
        lon = rec.get('lon', uk_center[1])
        
        # Create popup content
        popup_content = f"""
        <div style="width: 200px;">
            <h4>{rec['location']}</h4>
            <p><strong>BTR Score:</strong> {rec['overall_score']:.1f}/100</p>
        """
        
        # Add metrics if available
        if 'metrics' in rec:
            popup_content += "<ul>"
            for metric, score in rec['metrics'].items():
                popup_content += f"<li>{metric.replace('_', ' ').title()}: {score*100:.1f}%</li>"
            popup_content += "</ul>"
        
        popup_content += "</div>"
        
        # Determine color based on score
        color = get_score_color(rec['overall_score'])
        
        # Create marker
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=f"{rec['location']} - Score: {rec['overall_score']:.1f}",
            icon=folium.Icon(color='white', icon_color=color, icon='home', prefix='fa')
        ).add_to(marker_cluster)
    
    # Display map in Streamlit
    map_html = m._repr_html_()
    components.html(map_html, height=400)


def display_location_table(recommendations, strategy, weights):
    """Display a table of location recommendations"""
    st.subheader("Recommended Locations")
    
    # Create dataframe from recommendations
    data = []
    for rec in recommendations:
        row = {
            'Location': rec['location'],
            'Overall Score': f"{rec['overall_score']:.1f}",
            'Location Score': f"{rec['location_score']:.1f}",
        }
        
        # Add metric scores
        if 'metrics' in rec:
            for metric, score in rec['metrics'].items():
                row[metric.replace('_', ' ').title()] = f"{score*100:.1f}%"
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Style the dataframe
    st.dataframe(df, use_container_width=True)
    
    # Show strategy explanation
    st.write(f"### Strategy: {engine.strategies[strategy]['description']}")
    
    # Show weights used
    st.write("Weighting factors:")
    weight_data = []
    for metric, weight in weights.items():
        weight_data.append({
            'Factor': metric.replace('_', ' ').title(),
            'Weight': f"{weight*100:.0f}%"
        })
    
    weight_df = pd.DataFrame(weight_data)
    st.dataframe(weight_df, use_container_width=True)


def display_location_comparison_chart(recommendations):
    """Display a comparison chart of recommended locations"""
    st.subheader("Location Comparison")
    
    # Select metric to visualize
    available_metrics = ['overall_score', 'location_score']
    if recommendations and 'metrics' in recommendations[0]:
        available_metrics.extend(recommendations[0]['metrics'].keys())
    
    metric = st.selectbox(
        "Select metric to compare",
        available_metrics,
        format_func=lambda x: x.replace('_', ' ').title()
    )
    
    # Create data for chart
    locations = [rec['location'] for rec in recommendations]
    
    if metric == 'overall_score':
        values = [rec['overall_score'] for rec in recommendations]
        title = "Overall Score Comparison"
        y_label = "Score (0-100)"
    elif metric == 'location_score':
        values = [rec['location_score'] for rec in recommendations]
        title = "Location Score Comparison"
        y_label = "Score (0-100)"
    else:
        values = [rec['metrics'].get(metric, 0) * 100 for rec in recommendations]
        title = f"{metric.replace('_', ' ').title()} Comparison"
        y_label = "Score (%)"
    
    # Create bar chart
    fig = px.bar(
        x=locations, y=values,
        labels={"x": "Location", "y": y_label},
        title=title
    )
    
    # Add target line for key metrics
    if metric in ['rental_yield', 'profit_on_cost']:
        fig.add_hline(y=7.0, line_dash="dash", line_color="red", 
                     annotation_text="Good Yield Target (7%)")
    
    st.plotly_chart(fig, use_container_width=True)


def display_property_table(recommendations, strategy, weights):
    """Display a table of property recommendations"""
    st.subheader("Recommended Properties")
    
    # Create dataframe from recommendations
    data = []
    for rec in recommendations:
        property_info = rec['property']
        
        row = {
            'Address': f"{property_info.get('postcode', 'Unknown')}",
            'Price': f"£{property_info.get('price', 0):,.0f}",
            'Type': get_property_type_name(property_info.get('property_type')),
            'Overall Score': f"{rec['overall_score']:.1f}",
            'Location': rec['location'],
        }
        
        # Add metric scores
        if 'metrics' in rec:
            for metric, score in rec['metrics'].items():
                row[metric.replace('_', ' ').title()] = f"{score*100:.1f}%"
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Style the dataframe
    st.dataframe(df, use_container_width=True)


def display_property_comparison_chart(recommendations):
    """Display a comparison chart of recommended properties"""
    st.subheader("Property Comparison")
    
    # Select metric to visualize
    available_metrics = ['overall_score']
    if recommendations and 'metrics' in recommendations[0]:
        available_metrics.extend(recommendations[0]['metrics'].keys())
    
    metric = st.selectbox(
        "Select metric to compare",
        available_metrics,
        format_func=lambda x: x.replace('_', ' ').title(),
        key="property_metric"
    )
    
    # Create data for chart
    if recommendations:
        addresses = [rec['property'].get('postcode', 'Unknown') for rec in recommendations]
        
        if metric == 'overall_score':
            values = [rec['overall_score'] for rec in recommendations]
            title = "Overall Score Comparison"
            y_label = "Score (0-100)"
        else:
            values = [rec['metrics'].get(metric, 0) * 100 for rec in recommendations]
            title = f"{metric.replace('_', ' ').title()} Comparison"
            y_label = "Score (%)"
        
        # Create bar chart
        fig = px.bar(
            x=addresses, y=values,
            labels={"x": "Property", "y": y_label},
            title=title
        )
        
        st.plotly_chart(fig, use_container_width=True)


def get_score_color(score):
    """Get color based on score range"""
    if score >= 80:
        return '#1a9850'  # Green
    elif score >= 70:
        return '#91cf60'  # Light Green
    elif score >= 60:
        return '#d9ef8b'  # Yellow-Green
    elif score >= 50:
        return '#ffffbf'  # Yellow
    elif score >= 40:
        return '#fee08b'  # Light Orange
    elif score >= 30:
        return '#fc8d59'  # Orange
    else:
        return '#d73027'  # Red


def get_property_type_name(type_code):
    """Convert property type code to readable name"""
    type_map = {
        'D': 'Detached',
        'S': 'Semi-detached',
        'T': 'Terraced',
        'F': 'Flat/Maisonette',
        'O': 'Other'
    }
    
    return type_map.get(type_code, 'Unknown')