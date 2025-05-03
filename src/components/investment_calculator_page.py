import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(project_root)

from src.utils.data_processor import load_land_registry_data, load_ons_rental_data
from src.components.investment_calculator import BTRInvestmentCalculator

def display_investment_calculator():
    """Display the BTR investment calculator interface"""
    st.title("BTR Investment Calculator")
    
    # Initialize calculator
    calculator = BTRInvestmentCalculator()
    
    # Create tabs for different calculator options
    tab1, tab2, tab3 = st.tabs(["Property Analysis", "Scenario Comparison", "Maximum Purchase Price"])
    
    with tab1:
        display_property_analysis(calculator)
    
    with tab2:
        display_scenario_comparison(calculator)
    
    with tab3:
        display_max_purchase_price(calculator)


def display_property_analysis(calculator):
    """Display property analysis calculator"""
    st.header("Property Analysis")
    st.write("Calculate returns for a specific BTR investment property")
    
    # Property information inputs
    st.subheader("Property Information")
    col1, col2 = st.columns(2)
    
    with col1:
        purchase_price = st.number_input("Purchase Price (£)", value=250000, step=5000)
        square_feet = st.number_input("Property Size (sq ft)", value=1000, step=50)
        property_type = st.selectbox("Property Type", ["house", "flat"])
    
    with col2:
        rooms = st.number_input("Number of Rooms", value=3, step=1)
        is_leasehold = st.checkbox("Leasehold Property", value=property_type == "flat")
        postcode = st.text_input("Postcode", value="")
    
    # Refurbishment scenario selection
    st.subheader("Refurbishment Strategy")
    scenario_key = st.selectbox(
        "Refurbishment Type",
        list(calculator.scenarios.keys()),
        format_func=lambda x: calculator.scenarios[x]['description']
    )
    
    # Custom works
    st.write("Additional Works (Optional)")
    custom_col1, custom_col2 = st.columns(2)
    
    custom_works = {}
    with custom_col1:
        if st.checkbox("New Kitchen"):
            custom_works['kitchen'] = st.number_input("Number of Kitchens", value=1, min_value=1)
        
        if st.checkbox("New Bathroom"):
            custom_works['bathroom'] = st.number_input("Number of Bathrooms", value=1, min_value=1)
        
        if st.checkbox("Rewiring"):
            custom_works['rewiring'] = 1
    
    with custom_col2:
        if st.checkbox("New Boiler/Heating"):
            custom_works['new_boiler'] = 1
        
        if st.checkbox("New Roof"):
            custom_works['new_roof'] = 1
        
        if st.checkbox("Extensions"):
            if st.checkbox("Loft Extension"):
                extension_sqft = st.number_input("Extension Size (sq ft)", value=300, step=50)
                custom_works['loft_extension_psf'] = extension_sqft / calculator.cost_benchmarks['loft_extension_psf']
    
    # Finance settings
    st.subheader("Finance Settings")
    loan_to_cost = st.slider("Loan to Cost Ratio", 0.0, 1.0, 0.7, 0.05)
    interest_rate = st.slider("Interest Rate (%)", 1.0, 20.0, 7.0, 0.5) / 100
    term_months = st.slider("Term (Months)", 1, 36, 12, 1)
    
    custom_finance = {
        'loan_to_cost': loan_to_cost,
        'interest_rate': interest_rate,
        'term_months': term_months
    }
    
    # Create property info dict
    property_info = {
        'purchase_price': purchase_price,
        'square_feet': square_feet,
        'property_type': property_type,
        'rooms': rooms,
        'is_leasehold': is_leasehold,
        'postcode': postcode
    }
    
    if 'extension_sqft' in locals():
        property_info['extension_sqft'] = extension_sqft
    
    # Calculate button
    if st.button("Calculate Investment Returns"):
        with st.spinner("Calculating..."):
            # Run calculations
            purchase_costs = calculator.calculate_purchase_costs(purchase_price)
            refurb_costs = calculator.calculate_refurb_costs(property_info, scenario_key, custom_works)
            gdv_result = calculator.calculate_gdv(property_info, refurb_costs)
            finance_costs = calculator.calculate_financing_costs(purchase_costs, refurb_costs, custom_finance)
            selling_costs = calculator.calculate_selling_costs(gdv_result['gdv'])
            profit_result = calculator.calculate_profit(
                purchase_costs, refurb_costs, gdv_result['gdv'], 
                finance_costs, selling_costs
            )
            rental_result = calculator.calculate_rental_income(property_info, gdv_result)
            
            # Display results
            st.success("Calculation Complete")
            
            # Summary metrics
            st.subheader("Investment Summary")
            summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
            
            with summary_col1:
                st.metric("Total Investment", f"£{purchase_costs['total_purchase_costs'] + refurb_costs['total_refurb_cost']:,.0f}")
                st.metric("Profit", f"£{profit_result['profit']:,.0f}")
            
            with summary_col2:
                st.metric("GDV", f"£{gdv_result['gdv']:,.0f}")
                st.metric("Profit on Cost", f"{profit_result['profit_on_cost']*100:.1f}%")
            
            with summary_col3:
                st.metric("Monthly Rent", f"£{rental_result['monthly_rent']:,.0f}")
                st.metric("Net Yield", f"{rental_result['net_yield']*100:.2f}%")
            
            with summary_col4:
                st.metric("ROI", f"{profit_result['roi']*100:.1f}%")
                target_status = "✅ Met" if profit_result['profit_on_cost'] >= 0.25 else "❌ Not Met"
                st.metric("25% Profit Target", target_status)
            
            # Detailed breakdown
            st.subheader("Detailed Breakdown")
            
            # Create tabs for different breakdowns
            breakdown_tab1, breakdown_tab2, breakdown_tab3, breakdown_tab4 = st.tabs([
                "Costs & Profit", "Refurbishment", "Financing", "Rental Income"
            ])
            
            with breakdown_tab1:
                # Create Sankey diagram for cost flow
                costs_labels = [
                    "Purchase", "Refurbishment", "Finance", "Selling Costs", "GDV", "Profit"
                ]
                
                costs_values = [
                    purchase_costs['purchase_price'],
                    refurb_costs['total_refurb_cost'],
                    finance_costs['total_finance_cost'],
                    selling_costs['total_selling_costs'],
                    gdv_result['gdv'],
                    profit_result['profit']
                ]
                
                # Create stacked bar chart
                cost_fig = go.Figure()
                
                cost_fig.add_trace(go.Bar(
                    name='Purchase',
                    x=['Costs'],
                    y=[purchase_costs['purchase_price']],
                    marker_color='#1f77b4'
                ))
                
                cost_fig.add_trace(go.Bar(
                    name='Transaction Costs',
                    x=['Costs'],
                    y=[purchase_costs['total_purchase_costs'] - purchase_costs['purchase_price']],
                    marker_color='#ff7f0e'
                ))
                
                cost_fig.add_trace(go.Bar(
                    name='Refurbishment',
                    x=['Costs'],
                    y=[refurb_costs['total_refurb_cost']],
                    marker_color='#2ca02c'
                ))
                
                cost_fig.add_trace(go.Bar(
                    name='Finance',
                    x=['Costs'],
                    y=[finance_costs['total_finance_cost']],
                    marker_color='#d62728'
                ))
                
                cost_fig.add_trace(go.Bar(
                    name='Selling Costs',
                    x=['Costs'],
                    y=[selling_costs['total_selling_costs']],
                    marker_color='#9467bd'
                ))
                
                cost_fig.add_trace(go.Bar(
                    name='GDV',
                    x=['Revenue'],
                    y=[gdv_result['gdv']],
                    marker_color='#8c564b'
                ))
                
                cost_fig.update_layout(
                    title='Cost vs Revenue Breakdown',
                    barmode='stack',
                    xaxis_title='',
                    yaxis_title='Amount (£)',
                    height=500
                )
                
                st.plotly_chart(cost_fig, use_container_width=True)
                
                # Key metrics table
                st.write("### Key Metrics")
                metrics_df = pd.DataFrame({
                    'Metric': [
                        'Purchase Price', 'Transaction Costs', 'Refurbishment Costs',
                        'Finance Costs', 'Selling Costs', 'Total Costs',
                        'GDV', 'Profit', 'Profit on Cost', 'ROI'
                    ],
                    'Value': [
                        f"£{purchase_costs['purchase_price']:,.0f}",
                        f"£{purchase_costs['total_purchase_costs'] - purchase_costs['purchase_price']:,.0f}",
                        f"£{refurb_costs['total_refurb_cost']:,.0f}",
                        f"£{finance_costs['total_finance_cost']:,.0f}",
                        f"£{selling_costs['total_selling_costs']:,.0f}",
                        f"£{profit_result['total_costs']:,.0f}",
                        f"£{gdv_result['gdv']:,.0f}",
                        f"£{profit_result['profit']:,.0f}",
                        f"{profit_result['profit_on_cost']*100:.1f}%",
                        f"{profit_result['roi']*100:.1f}%"
                    ]
                })
                
                st.table(metrics_df)
            
            with breakdown_tab2:
                st.write(f"### {refurb_costs['description']}")
                st.write(f"Total Refurbishment Cost: £{refurb_costs['total_refurb_cost']:,.0f}")
                st.write(f"Refurbishment Cost per Sq Ft: £{refurb_costs['refurb_cost_psf']:.2f}")
                
                # Create breakdown chart
                refurb_items = []
                refurb_values = []
                
                for item, cost in refurb_costs['cost_breakdown'].items():
                    # Make item name more readable
                    readable_name = item.replace('_', ' ').title().replace('Psf', 'Per Sq Ft')
                    refurb_items.append(readable_name)
                    refurb_values.append(cost)
                
                # Add contingency and professional fees
                refurb_items.extend(['Contingency', 'Professional Fees'])
                refurb_values.extend([refurb_costs['contingency'], refurb_costs['professional_fees']])
                
                refurb_df = pd.DataFrame({
                    'Item': refurb_items,
                    'Cost': refurb_values
                })
                
                # Sort by cost (descending)
                refurb_df = refurb_df.sort_values('Cost', ascending=False)
                
                refurb_fig = go.Figure(go.Bar(
                    x=refurb_df['Cost'],
                    y=refurb_df['Item'],
                    orientation='h',
                    marker_color='#2ca02c'
                ))
                
                refurb_fig.update_layout(
                    title='Refurbishment Cost Breakdown',
                    xaxis_title='Cost (£)',
                    yaxis_title='',
                    height=400 + len(refurb_items) * 25
                )
                
                st.plotly_chart(refurb_fig, use_container_width=True)
            
            with breakdown_tab3:
                st.write("### Financing Details")
                st.write(f"Loan Amount: £{finance_costs['loan_amount']:,.0f}")
                st.write(f"Equity Required: £{finance_costs['equity_required']:,.0f}")
                
                # Create pie chart for financing
                finance_fig = go.Figure(data=[go.Pie(
                    labels=['Arrangement Fee', 'Interest', 'Exit Fee', 'Legal Costs'],
                    values=[
                        finance_costs['arrangement_fee'],
                        finance_costs['interest_cost'],
                        finance_costs['exit_fee'],
                        finance_costs['legal_costs']
                    ],
                    hole=.3
                )])
                
                finance_fig.update_layout(
                    title='Finance Cost Breakdown',
                    height=500
                )
                
                st.plotly_chart(finance_fig, use_container_width=True)
                
                # Finance metrics table
                finance_df = pd.DataFrame({
                    'Metric': [
                        'Loan Amount', 'Equity Required', 'Loan to Cost Ratio',
                        'Interest Rate', 'Term', 'Arrangement Fee',
                        'Exit Fee', 'Legal Costs', 'Interest', 'Total Finance Cost'
                    ],
                    'Value': [
                        f"£{finance_costs['loan_amount']:,.0f}",
                        f"£{finance_costs['equity_required']:,.0f}",
                        f"{loan_to_cost*100:.0f}%",
                        f"{interest_rate*100:.2f}%",
                        f"{term_months} months",
                        f"£{finance_costs['arrangement_fee']:,.0f}",
                        f"£{finance_costs['exit_fee']:,.0f}",
                        f"£{finance_costs['legal_costs']:,.0f}",
                        f"£{finance_costs['interest_cost']:,.0f}",
                        f"£{finance_costs['total_finance_cost']:,.0f}"
                    ]
                })
                
                st.table(finance_df)
            
            with breakdown_tab4:
                st.write("### Rental Income")
                st.write(f"Monthly Rent: £{rental_result['monthly_rent']:,.0f}")
                st.write(f"Annual Rent: £{rental_result['annual_rent']:,.0f}")
                st.write(f"Net Yield: {rental_result['net_yield']*100:.2f}%")
                
                # Create income vs expenses chart
                rental_fig = go.Figure()
                
                rental_fig.add_trace(go.Bar(
                    x=['Gross Income'],
                    y=[rental_result['annual_rent']],
                    name='Gross Rental Income',
                    marker_color='#1f77b4'
                ))
                
                # Add expense bars
                expense_categories = [
                    'Management Fee', 'Maintenance', 'Void Costs', 
                    'Insurance', 'Service Charge', 'Ground Rent'
                ]
                
                expense_values = [
                    rental_result['management_fee'],
                    rental_result['maintenance'],
                    rental_result['void_cost'],
                    rental_result['insurance'],
                    rental_result['service_charge'],
                    rental_result['ground_rent']
                ]
                
                for i, (cat, val) in enumerate(zip(expense_categories, expense_values)):
                    if val > 0:  # Only show non-zero expenses
                        rental_fig.add_trace(go.Bar(
                            x=['Expenses'],
                            y=[val],
                            name=cat,
                            marker_color=px.colors.qualitative.Plotly[i+1]
                        ))
                
                rental_fig.add_trace(go.Bar(
                    x=['Net Income'],
                    y=[rental_result['net_annual_rent']],
                    name='Net Rental Income',
                    marker_color='#2ca02c'
                ))
                
                rental_fig.update_layout(
                    title='Annual Rental Income Breakdown',
                    barmode='stack',
                    xaxis_title='',
                    yaxis_title='Amount (£)',
                    height=500
                )
                
                st.plotly_chart(rental_fig, use_container_width=True)
                
                # Rental metrics table
                rental_df = pd.DataFrame({
                    'Metric': [
                        'Monthly Rent', 'Annual Rent', 'Management Fee',
                        'Maintenance', 'Void Costs', 'Insurance',
                        'Service Charge', 'Ground Rent', 'Total Expenses',
                        'Net Annual Rent', 'Gross Yield', 'Net Yield'
                    ],
                    'Value': [
                        f"£{rental_result['monthly_rent']:,.0f}",
                        f"£{rental_result['annual_rent']:,.0f}",
                        f"£{rental_result['management_fee']:,.0f}",
                        f"£{rental_result['maintenance']:,.0f}",
                        f"£{rental_result['void_cost']:,.0f}",
                        f"£{rental_result['insurance']:,.0f}",
                        f"£{rental_result['service_charge']:,.0f}",
                        f"£{rental_result['ground_rent']:,.0f}",
                        f"£{rental_result['total_expenses']:,.0f}",
                        f"£{rental_result['net_annual_rent']:,.0f}",
                        f"{rental_result['gross_yield']*100:.2f}%",
                        f"{rental_result['net_yield']*100:.2f}%"
                    ]
                })
                
                st.table(rental_df)
            
            # Option to generate PDF report
            if st.button("Generate Investment Report (PDF)"):
                st.info("PDF Report Generation will be available in Week 3")


def display_scenario_comparison(calculator):
    """Display scenario comparison calculator"""
    st.header("Scenario Comparison")
    st.write("Compare different refurbishment strategies for the same property")
    
    # Property information inputs
    st.subheader("Property Information")
    col1, col2 = st.columns(2)
    
    with col1:
        purchase_price = st.number_input("Purchase Price (£)", value=250000, step=5000, key="sc_price")
        square_feet = st.number_input("Property Size (sq ft)", value=1000, step=50, key="sc_sqft")
        property_type = st.selectbox("Property Type", ["house", "flat"], key="sc_type")
    
    with col2:
        rooms = st.number_input("Number of Rooms", value=3, step=1, key="sc_rooms")
        is_leasehold = st.checkbox("Leasehold Property", value=property_type == "flat", key="sc_leasehold")
        postcode = st.text_input("Postcode", value="", key="sc_postcode")
    
    # Scenarios to compare
    st.subheader("Scenarios to Compare")
    scenarios = []
    
    for scenario_key in calculator.scenarios.keys():
        if st.checkbox(calculator.scenarios[scenario_key]['description'], value=True):
            scenarios.append(scenario_key)
    
    # Finance settings
    st.subheader("Finance Settings")
    loan_to_cost = st.slider("Loan to Cost Ratio", 0.0, 1.0, 0.7, 0.05, key="sc_ltc")
    interest_rate = st.slider("Interest Rate (%)", 1.0, 20.0, 7.0, 0.5, key="sc_interest") / 100
    term_months = st.slider("Term (Months)", 1, 36, 12, 1, key="sc_term")
    
    custom_finance = {
        'loan_to_cost': loan_to_cost,
        'interest_rate': interest_rate,
        'term_months': term_months
    }
    
    # Create property info dict
    property_info = {
        'purchase_price': purchase_price,
        'square_feet': square_feet,
        'property_type': property_type,
        'rooms': rooms,
        'is_leasehold': is_leasehold,
        'postcode': postcode
    }
    
    # Calculate button
    if st.button("Compare Scenarios"):
        with st.spinner("Calculating..."):
            if scenarios:
                # Run scenario analysis
                results = calculator.run_scenario_analysis(property_info, scenarios)
                
                # Display results
                st.success(f"Compared {len(scenarios)} scenarios")
                
                # Create comparison table
                comparison_data = []
                
                for scenario_key, scenario_results in results['scenarios'].items():
                    comparison_data.append({
                        'Scenario': calculator.scenarios[scenario_key]['description'],
                        'Refurb Cost': f"£{scenario_results['refurb_cost']:,.0f}",
                        'GDV': f"£{scenario_results['gdv']:,.0f}",
                        'Profit': f"£{scenario_results['profit']:,.0f}",
                        'Profit on Cost': f"{scenario_results['profit_on_cost']*100:.1f}%",
                        'ROI': f"{scenario_results['roi']*100:.1f}%",
                        'Monthly Rent': f"£{scenario_results['monthly_rent']:,.0f}",
                        'Net Yield': f"{scenario_results['net_yield']*100:.2f}%",
                        '25% Target': "✅" if scenario_results['target_met'] else "❌",
                        # Store numeric values for sorting/charting
                        '_refurb_cost': scenario_results['refurb_cost'],
                        '_profit': scenario_results['profit'],
                        '_profit_pct': scenario_results['profit_on_cost'] * 100,
                        '_roi': scenario_results['roi'] * 100,
                        '_rent': scenario_results['monthly_rent'],
                        '_yield': scenario_results['net_yield'] * 100
                    })
                
                comparison_df = pd.DataFrame(comparison_data)
                display_cols = ['Scenario', 'Refurb Cost', 'GDV', 'Profit', 
                              'Profit on Cost', 'ROI', 'Monthly Rent', 'Net Yield', '25% Target']
                
                st.table(comparison_df[display_cols])
                
                # Create comparison charts
                st.subheader("Visual Comparison")
                
                # Metrics selection
                chart_metric = st.selectbox(
                    "Select metric to visualize",
                    ["Profit", "Profit on Cost (%)", "ROI (%)", "Monthly Rent", "Net Yield (%)"]
                )
                
                # Map selection to dataframe column
                metric_map = {
                    "Profit": "_profit",
                    "Profit on Cost (%)": "_profit_pct",
                    "ROI (%)": "_roi",
                    "Monthly Rent": "_rent",
                    "Net Yield (%)": "_yield",
                }
                
                # Sort data by selected metric
                sorted_df = comparison_df.sort_values(metric_map[chart_metric], ascending=False)
                
                # Create bar chart
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=sorted_df['Scenario'],
                    y=sorted_df[metric_map[chart_metric]],
                    marker_color='#1f77b4'
                ))
                
                fig.update_layout(
                    title=f'Comparison by {chart_metric}',
                    xaxis_title='Scenario',
                    yaxis_title=chart_metric,
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Highlight best scenario
                best_scenario = results['best_scenario']
                best_description = calculator.scenarios[best_scenario]['description']
                best_profit = results['scenarios'][best_scenario]['profit_on_cost'] * 100
                
                st.success(f"Best Scenario: **{best_description}** with **{best_profit:.1f}%** profit on cost")
            else:
                st.error("Please select at least one scenario to compare")


def display_max_purchase_price(calculator):
    """Display maximum purchase price calculator"""
    st.header("Maximum Purchase Price Calculator")
    st.write("Calculate the maximum purchase price to achieve your target profit")
    
    # Property information inputs
    st.subheader("Property Information")
    col1, col2 = st.columns(2)
    
    with col1:
        square_feet = st.number_input("Property Size (sq ft)", value=1000, step=50, key="mp_sqft")
        property_type = st.selectbox("Property Type", ["house", "flat"], key="mp_type")
        rooms = st.number_input("Number of Rooms", value=3, step=1, key="mp_rooms")
    
    with col2:
        is_leasehold = st.checkbox("Leasehold Property", value=property_type == "flat", key="mp_leasehold")
        postcode = st.text_input("Postcode", value="", key="mp_postcode")
        target_profit = st.slider("Target Profit on Cost (%)", 15.0, 40.0, 25.0, 0.5, key="mp_profit") / 100
    
    # Refurbishment scenario
    st.subheader("Refurbishment Strategy")
    scenario_key = st.selectbox(
        "Refurbishment Type",
        list(calculator.scenarios.keys()),
        format_func=lambda x: calculator.scenarios[x]['description'],
        key="mp_scenario"
    )
    
    # Finance settings
    st.subheader("Finance Settings")
    loan_to_cost = st.slider("Loan to Cost Ratio", 0.0, 1.0, 0.7, 0.05, key="mp_ltc")
    interest_rate = st.slider("Interest Rate (%)", 1.0, 20.0, 7.0, 0.5, key="mp_interest") / 100
    term_months = st.slider("Term (Months)", 1, 36, 12, 1, key="mp_term")
    
    custom_finance = {
        'loan_to_cost': loan_to_cost,
        'interest_rate': interest_rate,
        'term_months': term_months
    }
    
    # Create property info dict (without purchase price)
    property_info = {
        'square_feet': square_feet,
        'property_type': property_type,
        'rooms': rooms,
        'is_leasehold': is_leasehold,
        'postcode': postcode
    }
    
    # Calculate button
    if st.button("Calculate Maximum Purchase Price"):
        with st.spinner("Calculating..."):
            # Calculate max purchase price
            max_price_result = calculator.calculate_max_purchase_price(
                property_info, 
                scenario_key=scenario_key,
                target_profit=target_profit,
                custom_finance_settings=custom_finance
            )
            
            # Display results
            st.success("Calculation Complete")
            
            # Show max purchase price
            st.subheader("Maximum Purchase Price")
            max_price = max_price_result['max_purchase_price']
            st.write(f"### £{max_price:,.0f}")
            st.write(f"To achieve a **{target_profit*100:.1f}%** profit on cost")
            
            # Key metrics
            st.subheader("Key Metrics")
            metrics_col1, metrics_col2 = st.columns(2)
            
            with metrics_col1:
                st.metric("Maximum Purchase Price", f"£{max_price:,.0f}")
                st.metric("Target Profit", f"{target_profit*100:.1f}%")
                st.metric("Achievable Profit", f"{max_price_result['achieved_profit']*100:.1f}%")
            
            with metrics_col2:
                st.metric("GDV", f"£{max_price_result['gdv']:,.0f}")
                st.metric("Total Costs", f"£{max_price_result['total_costs']:,.0f}")
                st.metric("Profit", f"£{max_price_result['profit']:,.0f}")
            
            # Price per square foot
            price_psf = max_price / square_feet
            st.write(f"Price per square foot: **£{price_psf:.0f}**")
            
            # Notes
            st.info("""
            **Note**: This is the maximum price you should pay to achieve your target profit.
            Always negotiate below this price to build in a margin of safety.
            """)
            
            # Price sensitivity analysis
            st.subheader("Price Sensitivity Analysis")
            st.write("How different purchase prices affect your profit on cost")
            
            # Create sensitivity data
            price_range = [max_price * (1 + adj/100) for adj in range(-20, 25, 5)]
            sensitivity_data = []
            
            for price in price_range:
                property_info_copy = property_info.copy()
                property_info_copy['purchase_price'] = price
                
                # Calculate all metrics for this price
                purchase_costs = calculator.calculate_purchase_costs(price)
                refurb_costs = calculator.calculate_refurb_costs(property_info_copy, scenario_key)
                gdv_result = calculator.calculate_gdv(property_info_copy, refurb_costs)
                finance_costs = calculator.calculate_financing_costs(purchase_costs, refurb_costs, custom_finance)
                selling_costs = calculator.calculate_selling_costs(gdv_result['gdv'])
                
                profit_result = calculator.calculate_profit(
                    purchase_costs, refurb_costs, gdv_result['gdv'], 
                    finance_costs, selling_costs
                )
                
                # Determine if target is met
                target_met = profit_result['profit_on_cost'] >= target_profit
                
                sensitivity_data.append({
                    'Purchase Price': f"£{price:,.0f}",
                    'Profit on Cost': f"{profit_result['profit_on_cost']*100:.1f}%",
                    'Profit': f"£{profit_result['profit']:,.0f}",
                    'Target Met': "✅" if target_met else "❌",
                    '_price': price,
                    '_profit_pct': profit_result['profit_on_cost'] * 100,
                    '_profit': profit_result['profit'],
                    '_target_met': target_met
                })
            
            sensitivity_df = pd.DataFrame(sensitivity_data)
            
            # Display table
            st.table(sensitivity_df[['Purchase Price', 'Profit on Cost', 'Profit', 'Target Met']])
            
            # Create sensitivity chart
            fig = go.Figure()
            
            # Add target profit line
            fig.add_trace(go.Scatter(
                x=sensitivity_df['_price'],
                y=[target_profit * 100] * len(sensitivity_df),
                mode='lines',
                name=f'Target Profit ({target_profit*100:.1f}%)',
                line=dict(color='red', dash='dash')
            ))
            
            # Add profit on cost line
            fig.add_trace(go.Scatter(
                x=sensitivity_df['_price'],
                y=sensitivity_df['_profit_pct'],
                mode='lines+markers',
                name='Profit on Cost (%)',
                line=dict(color='blue')
            ))
            
            # Highlight max purchase price
            fig.add_vline(
                x=max_price,
                line_width=2,
                line_dash="dash",
                line_color="green",
                annotation_text="Max Purchase Price",
                annotation_position="top right"
            )
            
            fig.update_layout(
                title='Profit Sensitivity to Purchase Price',
                xaxis_title='Purchase Price (£)',
                yaxis_title='Profit on Cost (%)',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)