import pandas as pd
import numpy as np

class BTRInvestmentCalculator:
    """
    Calculator for Buy-to-Rent investment analysis
    
    Based on Knight Frank report benchmarks and industry standards:
    - Light refurbishment: £60-75 psf
    - Conversions (office to residential): £180 psf
    - New builds (ground-up): £225 psf
    - HMO conversions: £30,000 per room
    - Target profit: 25% on cost
    """
    
    def __init__(self):
        # Default cost benchmarks (in £)
        self.cost_benchmarks = {
            'light_refurb_psf': 75,
            'medium_refurb_psf': 120,
            'conversion_psf': 180,
            'new_build_psf': 225,
            'hmo_per_room': 30000,
            'loft_extension_psf': 200,
            'basement_psf': 250,
            'kitchen': 15000,
            'bathroom': 7500,
            'rewiring': 5000,
            'replumbing': 6000,
            'painting_decorating_psf': 12,
            'flooring_psf': 25,
            'windows_per_unit': 800,
            'roof_repair': 8000,
            'new_roof': 15000,
            'landscaping': 5000,
            'driveway': 4500,
            'new_boiler': 3500,
            'new_heating_system': 8000
        }
        
        # Default scenario settings
        self.scenarios = {
            'cosmetic_refurb': {
                'description': 'Cosmetic refurbishment only (painting, decorating, minor works)',
                'costs': ['painting_decorating_psf', 'flooring_psf'],
                'value_uplift_pct': 0.10  # 10% value uplift
            },
            'light_refurb': {
                'description': 'Light refurbishment (cosmetic + kitchen/bathroom)',
                'costs': ['light_refurb_psf'],
                'value_uplift_pct': 0.15  # 15% value uplift
            },
            'medium_refurb': {
                'description': 'Medium refurbishment (light + some reconfiguration)',
                'costs': ['medium_refurb_psf'],
                'value_uplift_pct': 0.25  # 25% value uplift
            },
            'full_refurb': {
                'description': 'Full refurbishment (gutting and rebuilding interior)',
                'costs': ['conversion_psf'],
                'value_uplift_pct': 0.35  # 35% value uplift
            },
            'extension': {
                'description': 'Extending the property (e.g. loft conversion, rear extension)',
                'costs': ['loft_extension_psf'],
                'value_uplift_psf': 550  # £550 per sqft value added for new space
            }
        }
        
        # Default finance settings
        self.finance_settings = {
            'interest_rate': 0.14,  # 14% p.a.
            'loan_to_cost': 1.0,    # 100% LTC
            'term_months': 12,      # 12 month term
            'arrangement_fee_pct': 0.01,  # 1% arrangement fee
            'exit_fee_pct': 0.01,   # 1% exit fee
            'legal_costs': 2000,    # £2,000 legal costs
        }
        
        # Transaction costs
        self.transaction_costs = {
            'purchase_legal_pct': 0.01,  # 1% legal costs on purchase
            'purchase_legal_min': 1500,  # Minimum £1,500
            'survey': 1000,              # Survey cost
            'sdlt_thresholds': [125000, 250000, 925000, 1500000],
            'sdlt_rates': [0.02, 0.05, 0.10, 0.12],  # Additional 2% for BTR/second homes
            'selling_agent_pct': 0.015,   # 1.5% selling agent fee
            'selling_legal_pct': 0.005,   # 0.5% legal costs on sale
            'selling_legal_min': 1000,    # Minimum £1,000
        }
        
        # Rental income settings
        self.rental_settings = {
            'gross_yield': 0.05,          # 5% gross yield
            'management_fee_pct': 0.10,   # 10% management fee
            'maintenance_pct': 0.10,      # 10% of rent for maintenance
            'void_months_per_year': 0.5,  # 2 weeks void per year on average
            'insurance_pct': 0.005,       # 0.5% of property value for insurance
            'service_charge_psf': 3,      # £3 per sqft service charge (apartments)
            'ground_rent': 250,           # £250 ground rent per year (leasehold)
        }
    
    def calculate_purchase_costs(self, purchase_price):
        """Calculate the total costs of purchasing a property"""
        # Legal costs
        legal_cost = max(purchase_price * self.transaction_costs['purchase_legal_pct'], 
                         self.transaction_costs['purchase_legal_min'])
        
        # Survey
        survey_cost = self.transaction_costs['survey']
        
        # Stamp Duty Land Tax (including 2% surcharge for BTR investors)
        sdlt = self._calculate_sdlt(purchase_price)
        
        total_purchase_costs = legal_cost + survey_cost + sdlt
        
        return {
            'purchase_price': purchase_price,
            'legal_costs': legal_cost,
            'survey_costs': survey_cost,
            'stamp_duty': sdlt,
            'total_purchase_costs': purchase_price + total_purchase_costs,
            'transaction_costs_pct': total_purchase_costs / purchase_price
        }
    
    def _calculate_sdlt(self, purchase_price):
        """Calculate Stamp Duty Land Tax (including BTR/second home surcharge)"""
        thresholds = self.transaction_costs['sdlt_thresholds']
        rates = self.transaction_costs['sdlt_rates']
        
        sdlt = 0
        remaining = purchase_price
        
        for i in range(len(thresholds)):
            if i == 0:
                band_size = thresholds[i]
            else:
                band_size = thresholds[i] - thresholds[i-1]
            
            if remaining > band_size:
                sdlt += band_size * rates[i]
                remaining -= band_size
            else:
                sdlt += remaining * rates[i]
                break
        
        # If property is above the top threshold
        if remaining > 0:
            sdlt += remaining * rates[-1]
        
        return sdlt
    
    def calculate_refurb_costs(self, property_info, scenario_key='light_refurb', custom_works=None):
        """
        Calculate refurbishment costs
        
        Parameters:
        -----------
        property_info : dict
            Property information including square footage, number of rooms, etc.
        scenario_key : str
            Key for predefined scenario
        custom_works : dict, optional
            Custom works to include (e.g. {'kitchen': 1, 'bathroom': 2})
        
        Returns:
        --------
        dict
            Refurbishment cost breakdown
        """
        scenario = self.scenarios.get(scenario_key)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_key}")
        
        # Get property details (with defaults)
        sqft = property_info.get('square_feet', 1000)
        rooms = property_info.get('rooms', 3)
        
        # Calculate base costs from scenario
        costs = {}
        subtotal = 0
        
        for cost_key in scenario['costs']:
            if cost_key.endswith('_psf'):
                # Per square foot cost
                cost = self.cost_benchmarks[cost_key] * sqft
                costs[cost_key] = cost
                subtotal += cost
            elif cost_key.endswith('_per_room'):
                # Per room cost
                cost = self.cost_benchmarks[cost_key] * rooms
                costs[cost_key] = cost
                subtotal += cost
            else:
                # Fixed cost
                cost = self.cost_benchmarks[cost_key]
                costs[cost_key] = cost
                subtotal += cost
        
        # Add custom works if specified
        if custom_works:
            for work, quantity in custom_works.items():
                if work in self.cost_benchmarks:
                    cost = self.cost_benchmarks[work] * quantity
                    costs[work] = cost
                    subtotal += cost
        
        # Add contingency (10%)
        contingency = subtotal * 0.10
        
        # Add professional fees (12% - architects, structural engineers, etc.)
        if scenario_key in ['full_refurb', 'extension']:
            professional_fees = subtotal * 0.12
        else:
            professional_fees = subtotal * 0.05  # Lower for simpler works
        
        # Calculate total
        total_refurb = subtotal + contingency + professional_fees
        
        return {
            'scenario': scenario_key,
            'description': scenario['description'],
            'square_feet': sqft,
            'rooms': rooms,
            'cost_breakdown': costs,
            'subtotal': subtotal,
            'contingency': contingency,
            'professional_fees': professional_fees,
            'total_refurb_cost': total_refurb,
            'refurb_cost_psf': total_refurb / sqft
        }
    
    def calculate_gdv(self, property_info, refurb_result, comparable_data=None):
        """
        Calculate Gross Development Value after refurbishment
        
        Parameters:
        -----------
        property_info : dict
            Property information including purchase price
        refurb_result : dict
            Output from calculate_refurb_costs
        comparable_data : dict, optional
            Comparable sales data to use instead of formula
            
        Returns:
        --------
        dict
            GDV and related metrics
        """
        purchase_price = property_info.get('purchase_price', 0)
        sqft = property_info.get('square_feet', 1000)
        
        scenario_key = refurb_result['scenario']
        scenario = self.scenarios.get(scenario_key)
        
        # Calculate GDV based on scenario
        if scenario_key == 'extension':
            # Extension adds value based on new square footage
            extension_sqft = property_info.get('extension_sqft', sqft * 0.25)  # Default 25% increase
            existing_value = purchase_price
            extension_value = extension_sqft * scenario['value_uplift_psf']
            gdv = existing_value + extension_value
        else:
            # Other scenarios add percentage to value
            gdv = purchase_price * (1 + scenario['value_uplift_pct'])
        
        # Override with comparable data if provided
        if comparable_data and 'avg_price_psf' in comparable_data:
            comp_price_psf = comparable_data['avg_price_psf']
            gdv = sqft * comp_price_psf
        
        return {
            'purchase_price': purchase_price,
            'refurb_cost': refurb_result['total_refurb_cost'],
            'gdv': gdv,
            'value_uplift': gdv - purchase_price,
            'value_uplift_pct': (gdv - purchase_price) / purchase_price,
            'gdv_psf': gdv / sqft
        }
    
    def calculate_rental_income(self, property_info, gdv_result, rental_market_data=None):
        """
        Calculate projected rental income and yield
        
        Parameters:
        -----------
        property_info : dict
            Property information
        gdv_result : dict
            Output from calculate_gdv
        rental_market_data : dict, optional
            Local rental market data to override defaults
            
        Returns:
        --------
        dict
            Rental income projections and metrics
        """
        # Get property details
        sqft = property_info.get('square_feet', 1000)
        property_type = property_info.get('property_type', 'house')  # 'house' or 'flat'
        is_leasehold = property_info.get('is_leasehold', property_type == 'flat')
        
        # Get GDV (post-refurb value)
        gdv = gdv_result['gdv']
        
        # Calculate gross rental income
        gross_yield = rental_market_data.get('gross_yield') if rental_market_data else self.rental_settings['gross_yield']
        annual_rent = gdv * gross_yield
        monthly_rent = annual_rent / 12
        
        # Calculate expenses
        management_fee = annual_rent * self.rental_settings['management_fee_pct']
        maintenance = annual_rent * self.rental_settings['maintenance_pct']
        void_cost = annual_rent * (self.rental_settings['void_months_per_year'] / 12)
        insurance = gdv * self.rental_settings['insurance_pct']
        
        # Service charge and ground rent for leasehold properties
        service_charge = 0
        ground_rent = 0
        if is_leasehold:
            service_charge = sqft * self.rental_settings['service_charge_psf']
            ground_rent = self.rental_settings['ground_rent']
        
        # Total expenses
        total_expenses = management_fee + maintenance + void_cost + insurance + service_charge + ground_rent
        
        # Net rental income
        net_annual_rent = annual_rent - total_expenses
        net_monthly_rent = net_annual_rent / 12
        
        # Yield calculations
        total_investment = property_info.get('purchase_price', 0) + gdv_result['refurb_cost']
        gross_yield = annual_rent / total_investment
        net_yield = net_annual_rent / total_investment
        
        return {
            'monthly_rent': monthly_rent,
            'annual_rent': annual_rent,
            'management_fee': management_fee,
            'maintenance': maintenance,
            'void_cost': void_cost,
            'insurance': insurance,
            'service_charge': service_charge,
            'ground_rent': ground_rent,
            'total_expenses': total_expenses,
            'net_monthly_rent': net_monthly_rent,
            'net_annual_rent': net_annual_rent,
            'gross_yield': gross_yield,
            'net_yield': net_yield,
            'expense_ratio': total_expenses / annual_rent
        }
    
    def calculate_financing_costs(self, purchase_costs, refurb_costs, 
                                 custom_finance_settings=None):
        """
        Calculate financing costs for the project
        
        Parameters:
        -----------
        purchase_costs : dict
            Output from calculate_purchase_costs
        refurb_costs : dict
            Output from calculate_refurb_costs
        custom_finance_settings : dict, optional
            Custom finance settings to override defaults
            
        Returns:
        --------
        dict
            Financing costs and metrics
        """
        # Use custom settings if provided, otherwise defaults
        settings = custom_finance_settings or self.finance_settings
        
        # Calculate total project cost
        purchase_price = purchase_costs['purchase_price']
        purchase_costs_total = purchase_costs['total_purchase_costs']
        refurb_total = refurb_costs['total_refurb_cost']
        
        total_project_cost = purchase_costs_total + refurb_total
        
        # Calculate loan amount
        loan_to_cost = settings.get('loan_to_cost', self.finance_settings['loan_to_cost'])
        loan_amount = total_project_cost * loan_to_cost
        
        # Calculate fees
        arrangement_fee = loan_amount * settings.get('arrangement_fee_pct', 
                                                   self.finance_settings['arrangement_fee_pct'])
        
        exit_fee = loan_amount * settings.get('exit_fee_pct',
                                            self.finance_settings['exit_fee_pct'])
        
        legal_costs = settings.get('legal_costs', self.finance_settings['legal_costs'])
        
        # Calculate interest
        interest_rate = settings.get('interest_rate', self.finance_settings['interest_rate'])
        term_months = settings.get('term_months', self.finance_settings['term_months'])
        
        # Simple interest calculation (can be enhanced for drawdowns)
        annual_interest = loan_amount * interest_rate
        interest_cost = annual_interest * (term_months / 12)
        
        # Total financing costs
        total_finance_cost = arrangement_fee + exit_fee + legal_costs + interest_cost
        
        return {
            'total_project_cost': total_project_cost,
            'loan_amount': loan_amount,
            'equity_required': total_project_cost - loan_amount,
            'arrangement_fee': arrangement_fee,
            'exit_fee': exit_fee,
            'legal_costs': legal_costs,
            'interest_cost': interest_cost,
            'total_finance_cost': total_finance_cost,
            'finance_cost_pct': total_finance_cost / loan_amount
        }
    
    def calculate_selling_costs(self, gdv):
        """
        Calculate the costs associated with selling the property
        
        Parameters:
        -----------
        gdv : float
            Gross Development Value (selling price)
            
        Returns:
        --------
        dict
            Selling costs and metrics
        """
        # Agent fees
        agent_fee = gdv * self.transaction_costs['selling_agent_pct']
        
        # Legal costs
        legal_cost = max(gdv * self.transaction_costs['selling_legal_pct'],
                        self.transaction_costs['selling_legal_min'])
        
        # Total selling costs
        total_selling_costs = agent_fee + legal_cost
        
        return {
            'agent_fee': agent_fee,
            'legal_costs': legal_cost,
            'total_selling_costs': total_selling_costs,
            'selling_costs_pct': total_selling_costs / gdv
        }
    
    def calculate_profit(self, purchase_costs, refurb_costs, gdv, finance_costs, selling_costs):
        """
        Calculate profit metrics for the project
        
        Parameters:
        -----------
        purchase_costs : dict
            Output from calculate_purchase_costs
        refurb_costs : dict
            Output from calculate_refurb_costs
        gdv : float
            Gross Development Value
        finance_costs : dict
            Output from calculate_financing_costs
        selling_costs : dict
            Output from calculate_selling_costs
            
        Returns:
        --------
        dict
            Profit metrics
        """
        # Total costs
        total_costs = (
            purchase_costs['total_purchase_costs'] +
            refurb_costs['total_refurb_cost'] +
            finance_costs['total_finance_cost'] +
            selling_costs['total_selling_costs']
        )
        
        # Calculate profit
        profit = gdv - total_costs
        
        # Calculate profit metrics
        profit_on_cost = profit / total_costs
        profit_on_gdv = profit / gdv
        
        # Calculate ROI
        equity_required = finance_costs['equity_required']
        roi = profit / equity_required if equity_required > 0 else float('inf')
        
        return {
            'total_costs': total_costs,
            'profit': profit,
            'profit_on_cost': profit_on_cost,
            'profit_on_gdv': profit_on_gdv,
            'roi': roi,
            'target_profit_achieved': profit_on_cost >= 0.25  # 25% target
        }
    
    def calculate_max_purchase_price(self, property_info, scenario_key='light_refurb', 
                                   target_profit=0.25, comparable_data=None,
                                   custom_finance_settings=None):
        """
        Calculate the maximum purchase price to achieve target profit
        
        Parameters:
        -----------
        property_info : dict
            Property information
        scenario_key : str
            Refurbishment scenario key
        target_profit : float
            Target profit on cost (default 0.25 / 25%)
        comparable_data : dict, optional
            Comparable sales data
        custom_finance_settings : dict, optional
            Custom finance settings
            
        Returns:
        --------
        dict
            Maximum purchase price and related metrics
        """
        # Start with an estimated purchase price
        if 'purchase_price' in property_info:
            initial_price = property_info['purchase_price']
        else:
            # Make a guess based on square footage
            sqft = property_info.get('square_feet', 1000)
            initial_price = sqft * 400  # £400 per sqft initial guess
        
        property_info_copy = property_info.copy()
        
        # Binary search to find maximum price
        min_price = 0
        max_price = initial_price * 2
        current_price = initial_price
        
        for _ in range(10):  # Max 10 iterations for convergence
            property_info_copy['purchase_price'] = current_price
            
            # Calculate all costs and profit
            purchase_costs = self.calculate_purchase_costs(current_price)
            refurb_costs = self.calculate_refurb_costs(property_info_copy, scenario_key)
            gdv_result = self.calculate_gdv(property_info_copy, refurb_costs, comparable_data)
            finance_costs = self.calculate_financing_costs(purchase_costs, refurb_costs, custom_finance_settings)
            selling_costs = self.calculate_selling_costs(gdv_result['gdv'])
            
            profit_result = self.calculate_profit(
                purchase_costs, refurb_costs, gdv_result['gdv'], 
                finance_costs, selling_costs
            )
            
            current_profit = profit_result['profit_on_cost']
            
            # Adjust price based on profit
            if abs(current_profit - target_profit) < 0.005:  # Within 0.5% of target
                break
                
            if current_profit > target_profit:
                # We can pay more
                min_price = current_price
                current_price = (current_price + max_price) / 2
            else:
                # We need to pay less
                max_price = current_price
                current_price = (current_price + min_price) / 2
        
        return {
            'max_purchase_price': current_price,
            'target_profit': target_profit,
            'achieved_profit': current_profit,
            'gdv': gdv_result['gdv'],
            'total_costs': profit_result['total_costs'],
            'profit': profit_result['profit']
        }
    
    def run_scenario_analysis(self, property_info, scenarios=None):
        """
        Run analysis for multiple refurbishment scenarios
        
        Parameters:
        -----------
        property_info : dict
            Property information
        scenarios : list, optional
            List of scenario keys to analyze (default: all scenarios)
            
        Returns:
        --------
        dict
            Results for all scenarios with metrics for comparison
        """
        if scenarios is None:
            scenarios = list(self.scenarios.keys())
        
        results = {}
        
        for scenario_key in scenarios:
            # Calculate all components
            purchase_costs = self.calculate_purchase_costs(property_info['purchase_price'])
            refurb_costs = self.calculate_refurb_costs(property_info, scenario_key)
            gdv_result = self.calculate_gdv(property_info, refurb_costs)
            finance_costs = self.calculate_financing_costs(purchase_costs, refurb_costs)
            selling_costs = self.calculate_selling_costs(gdv_result['gdv'])
            
            profit_result = self.calculate_profit(
                purchase_costs, refurb_costs, gdv_result['gdv'], 
                finance_costs, selling_costs
            )
            
            # Calculate rental metrics
            rental_result = self.calculate_rental_income(property_info, gdv_result)
            
            # Store results
            results[scenario_key] = {
                'description': self.scenarios[scenario_key]['description'],
                'purchase_price': property_info['purchase_price'],
                'refurb_cost': refurb_costs['total_refurb_cost'],
                'total_costs': profit_result['total_costs'],
                'gdv': gdv_result['gdv'],
                'profit': profit_result['profit'],
                'profit_on_cost': profit_result['profit_on_cost'],
                'roi': profit_result['roi'],
                'monthly_rent': rental_result['monthly_rent'],
                'net_yield': rental_result['net_yield'],
                'target_met': profit_result['target_profit_achieved']
            }
        
        # Find best scenario
        best_scenario = max(results.items(), key=lambda x: x[1]['profit_on_cost'])[0]
        
        return {
            'scenarios': results,
            'best_scenario': best_scenario,
            'best_profit_on_cost': results[best_scenario]['profit_on_cost'],
            'property_info': property_info
        }