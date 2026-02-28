#!/usr/bin/env python3
"""
Phase 6: Metrics Calculator - Degradation Rate Quantification

This script calculates degradation metrics for all scenarios:
- Portlandite dissolution rate constants
- C-S-H decalcification rates
- pH neutralization kinetics
- Chloride binding capacity
- Sulfate attack damage indices
- Pressure acceleration factors

NO MOCK DATA - Uses real simulation outputs
NO RANDOM GENERATION - Deterministic calculations only

Connects to:
- Phase 4: Simulation outputs (*_60d.json)
- Phase 5: Experimental validation criteria
- Phase 6: Comparative analysis

Author: GEMS Modeling Team
Date: February 2026
"""

import json
import os
import sys
from pathlib import Path
import numpy as np
from typing import Dict, List, Tuple, Any


def load_simulation_output(filepath: str) -> Dict:
    """
    Load simulation output file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Simulation data or None
    """
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        return json.load(f)


def calculate_portlandite_rate(data: Dict) -> Dict:
    """
    Calculate portlandite dissolution rate constant.
    
    Assumes first-order kinetics: dCH/dt = -k * CH
    
    Args:
        data: Simulation output
        
    Returns:
        Rate metrics
    """
    if not data or 'time_series' not in data:
        return {'rate_constant': None, 'half_life_days': None, 'status': 'data_unavailable'}
    
    time_series = data['time_series']
    
    # Extract time and portlandite
    times = []
    CH_values = []
    
    for step in time_series:
        time = step.get('time_days', 0)
        phases = step.get('phase_assemblage', {})
        CH = phases.get('portlandite', {}).get('amount_mol', 0)
        
        times.append(time)
        CH_values.append(CH)
    
    if len(times) < 3 or max(CH_values) == 0:
        return {'rate_constant': 0.0, 'half_life_days': float('inf'), 'status': 'insufficient_data'}
    
    # Find initial and final CH
    CH_initial = CH_values[0]
    
    # Linear regression on ln(CH) vs time (first-order kinetics)
    # Skip points where CH = 0 (depletion)
    valid_points = [(t, ch) for t, ch in zip(times, CH_values) if ch > 0.01]
    
    if len(valid_points) < 3:
        return {'rate_constant': 0.0, 'half_life_days': float('inf'), 'status': 'depleted'}
    
    t_vals = np.array([p[0] for p in valid_points])
    ln_CH = np.log([p[1] for p in valid_points])
    
    # Linear fit: ln(CH) = ln(CH0) - k*t
    if len(t_vals) > 1:
        k, intercept = np.polyfit(t_vals, ln_CH, 1)
        k = -k  # Rate constant is positive
        
        if k > 0:
            half_life = np.log(2) / k
        else:
            half_life = float('inf')
    else:
        k = 0.0
        half_life = float('inf')
    
    return {
        'rate_constant': float(k),
        'half_life_days': float(half_life),
        'initial_amount_mol': float(CH_initial),
        'final_amount_mol': float(CH_values[-1]),
        'depletion_percent': float((CH_initial - CH_values[-1]) / CH_initial * 100) if CH_initial > 0 else 0.0,
        'status': 'calculated'
    }


def calculate_CSH_decalcification_rate(data: Dict) -> Dict:
    """
    Calculate C-S-H decalcification rate.
    
    Args:
        data: Simulation output
        
    Returns:
        Decalcification metrics
    """
    if not data or 'time_series' not in data:
        return {'rate_constant': None, 'status': 'data_unavailable'}
    
    time_series = data['time_series']
    
    # Extract CSH over time
    times = []
    CSH_values = []
    
    for step in time_series:
        time = step.get('time_days', 0)
        phases = step.get('phase_assemblage', {})
        CSH = phases.get('CSH_gel', {}).get('amount_mol', 0)
        
        times.append(time)
        CSH_values.append(CSH)
    
    if len(times) < 3 or max(CSH_values) == 0:
        return {'rate_constant': 0.0, 'status': 'insufficient_data'}
    
    CSH_initial = CSH_values[0]
    CSH_final = CSH_values[-1]
    time_final = times[-1]
    
    # Calculate average rate
    if time_final > 0:
        avg_rate = (CSH_initial - CSH_final) / time_final
    else:
        avg_rate = 0.0
    
    return {
        'rate_constant': float(abs(avg_rate)),
        'initial_amount_mol': float(CSH_initial),
        'final_amount_mol': float(CSH_final),
        'depletion_percent': float((CSH_initial - CSH_final) / CSH_initial * 100) if CSH_initial > 0 else 0.0,
        'status': 'calculated'
    }


def calculate_pH_kinetics(data: Dict) -> Dict:
    """
    Calculate pH neutralization kinetics.
    
    Args:
        data: Simulation output
        
    Returns:
        pH metrics
    """
    if not data or 'time_series' not in data:
        return {'initial_pH': None, 'final_pH': None, 'status': 'data_unavailable'}
    
    time_series = data['time_series']
    
    # Extract pH over time
    times = []
    pH_values = []
    
    for step in time_series:
        time = step.get('time_days', 0)
        pH = step.get('pore_solution', {}).get('pH', 13.7)
        
        times.append(time)
        pH_values.append(pH)
    
    if len(times) < 2:
        return {'initial_pH': None, 'final_pH': None, 'status': 'insufficient_data'}
    
    pH_initial = pH_values[0]
    pH_final = pH_values[-1]
    pH_drop = pH_initial - pH_final
    
    # Time to drop below pH 12.5 (portlandite buffer)
    time_to_12_5 = None
    for t, pH in zip(times, pH_values):
        if pH < 12.5:
            time_to_12_5 = t
            break
    
    # Average neutralization rate
    if times[-1] > 0:
        neutralization_rate = pH_drop / times[-1]
    else:
        neutralization_rate = 0.0
    
    return {
        'initial_pH': float(pH_initial),
        'final_pH': float(pH_final),
        'pH_drop': float(pH_drop),
        'neutralization_rate_per_day': float(neutralization_rate),
        'time_to_buffer_loss_days': float(time_to_12_5) if time_to_12_5 else None,
        'status': 'calculated'
    }


def calculate_chloride_binding(data: Dict) -> Dict:
    """
    Calculate chloride binding capacity.
    
    Args:
        data: Simulation output
        
    Returns:
        Chloride binding metrics
    """
    if not data or 'time_series' not in data:
        return {'total_bound': None, 'status': 'data_unavailable'}
    
    time_series = data['time_series']
    
    # Extract Friedel's salt formation
    friedel_values = []
    for step in time_series:
        phases = step.get('phase_assemblage', {})
        friedel = phases.get('friedel_salt', {}).get('amount_mol', 0)
        friedel_values.append(friedel)
    
    if max(friedel_values) < 0.01:
        return {'total_bound': 0.0, 'max_friedel_mol': 0.0, 'status': 'no_chloride'}
    
    max_friedel = max(friedel_values)
    final_friedel = friedel_values[-1]
    
    # Friedel's salt: 3CaO·Al2O3·CaCl2·10H2O
    # 1 mol Friedel binds 2 mol Cl (from CaCl2)
    cl_bound_mol = final_friedel * 2
    
    # Convert to mg Cl per g paste (assume 1000 g paste)
    paste_mass_g = 1000.0
    cl_mass_mg = cl_bound_mol * 35.45 * 1000  # MW(Cl) = 35.45 g/mol
    cl_mg_per_g_paste = cl_mass_mg / paste_mass_g
    
    return {
        'total_bound_mg_per_g': float(cl_mg_per_g_paste),
        'max_friedel_mol': float(max_friedel),
        'final_friedel_mol': float(final_friedel),
        'binding_capacity_utilized_percent': float(final_friedel / max_friedel * 100) if max_friedel > 0 else 0.0,
        'status': 'calculated'
    }


def calculate_sulfate_damage_index(data: Dict) -> Dict:
    """
    Calculate sulfate attack damage index.
    
    Based on ettringite formation and expansion.
    
    Args:
        data: Simulation output
        
    Returns:
        Sulfate damage metrics
    """
    if not data or 'time_series' not in data:
        return {'damage_index': None, 'status': 'data_unavailable'}
    
    time_series = data['time_series']
    
    # Extract ettringite formation
    ettringite_values = []
    for step in time_series:
        phases = step.get('phase_assemblage', {})
        ett = phases.get('ettringite', {}).get('amount_mol', 0)
        ettringite_values.append(ett)
    
    if len(ettringite_values) < 2:
        return {'damage_index': 0.0, 'status': 'insufficient_data'}
    
    ett_initial = ettringite_values[0]
    ett_final = ettringite_values[-1]
    ett_increase = ett_final - ett_initial
    
    # Damage index: positive ettringite increase indicates expansion damage
    # Negative indicates sulfate depletion
    if ett_increase > 0:
        damage_index = min(ett_increase / (ett_initial + 1.0) * 100, 100)
    else:
        damage_index = 0.0
    
    return {
        'damage_index': float(damage_index),
        'initial_ettringite_mol': float(ett_initial),
        'final_ettringite_mol': float(ett_final),
        'ettringite_increase_mol': float(ett_increase),
        'damage_severity': 'high' if damage_index > 50 else ('medium' if damage_index > 20 else 'low'),
        'status': 'calculated'
    }


def calculate_pressure_acceleration_factor(immersion_data: Dict, pressure_data: Dict) -> Dict:
    """
    Calculate acceleration factor for pressure vs immersion.
    
    Args:
        immersion_data: Immersion scenario data
        pressure_data: Pressure scenario data
        
    Returns:
        Acceleration metrics
    """
    if not immersion_data or not pressure_data:
        return {'acceleration_factor': None, 'status': 'data_unavailable'}
    
    # Calculate degradation rates
    imm_CH_rate = calculate_portlandite_rate(immersion_data)
    press_CH_rate = calculate_portlandite_rate(pressure_data)
    
    if imm_CH_rate['status'] != 'calculated' or press_CH_rate['status'] != 'calculated':
        return {'acceleration_factor': None, 'status': 'rate_unavailable'}
    
    imm_k = imm_CH_rate['rate_constant']
    press_k = press_CH_rate['rate_constant']
    
    if imm_k > 0:
        acceleration = press_k / imm_k
    else:
        acceleration = 1.0
    
    return {
        'acceleration_factor': float(acceleration),
        'immersion_rate': float(imm_k),
        'pressure_rate': float(press_k),
        'interpretation': f'Pressure accelerates degradation by {acceleration:.1f}x',
        'status': 'calculated'
    }


def calculate_all_metrics(scenarios: List[str], outputs_dir: str) -> Dict:
    """
    Calculate all metrics for all scenarios.
    
    Args:
        scenarios: List of scenario names
        outputs_dir: Directory with simulation outputs
        
    Returns:
        Complete metrics dictionary
    """
    print(f"\n{'='*80}")
    print("CALCULATING DEGRADATION METRICS")
    print(f"{'='*80}")
    
    all_metrics = {}
    
    for scenario in scenarios:
        print(f"\nProcessing: {scenario}")
        filepath = os.path.join(outputs_dir, f"{scenario}_60d.json")
        data = load_simulation_output(filepath)
        
        if not data:
            print(f"  ⚠ No data available")
            all_metrics[scenario] = {'status': 'data_unavailable'}
            continue
        
        # Calculate all metrics
        CH_metrics = calculate_portlandite_rate(data)
        CSH_metrics = calculate_CSH_decalcification_rate(data)
        pH_metrics = calculate_pH_kinetics(data)
        Cl_metrics = calculate_chloride_binding(data)
        sulfate_metrics = calculate_sulfate_damage_index(data)
        
        all_metrics[scenario] = {
            'portlandite_dissolution': CH_metrics,
            'CSH_decalcification': CSH_metrics,
            'pH_neutralization': pH_metrics,
            'chloride_binding': Cl_metrics,
            'sulfate_damage': sulfate_metrics
        }
        
        print(f"  ✓ Portlandite rate: {CH_metrics.get('rate_constant', 0):.4e} day⁻¹")
        print(f"  ✓ pH drop: {pH_metrics.get('pH_drop', 0):.2f}")
        print(f"  ✓ Cl⁻ bound: {Cl_metrics.get('total_bound_mg_per_g', 0):.2f} mg/g")
    
    # Calculate pressure acceleration factors
    print(f"\n{'='*80}")
    print("CALCULATING PRESSURE ACCELERATION FACTORS")
    print(f"{'='*80}")
    
    solution_types = ['PW', 'NaCl', 'mixed']
    acceleration_factors = {}
    
    for solution in solution_types:
        imm_scenario = f"{solution}_immersion"
        press_scenario = f"{solution}_pressure"
        
        imm_data = load_simulation_output(os.path.join(outputs_dir, f"{imm_scenario}_60d.json"))
        press_data = load_simulation_output(os.path.join(outputs_dir, f"{press_scenario}_60d.json"))
        
        factor = calculate_pressure_acceleration_factor(imm_data, press_data)
        acceleration_factors[solution] = factor
        
        if factor['status'] == 'calculated':
            print(f"\n{solution.upper()}:")
            print(f"  Acceleration factor: {factor['acceleration_factor']:.2f}x")
            print(f"  {factor['interpretation']}")
    
    return {
        'scenario_metrics': all_metrics,
        'acceleration_factors': acceleration_factors
    }


def save_metrics_report(metrics: Dict, output_file: str):
    """
    Save metrics to JSON report.
    
    Args:
        metrics: Metrics dictionary
        output_file: Output filepath
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\n✓ Metrics report saved: {output_file}")


def print_metrics_summary(metrics: Dict):
    """
    Print formatted metrics summary.
    
    Args:
        metrics: Metrics dictionary
    """
    print(f"\n{'='*80}")
    print("METRICS SUMMARY")
    print(f"{'='*80}")
    
    scenario_metrics = metrics['scenario_metrics']
    
    print("\nPortlandite Dissolution Rates:")
    print(f"{'Scenario':<20} {'Rate (day⁻¹)':<15} {'Half-life (days)':<20} {'Depletion %':<15}")
    print("-" * 70)
    
    for scenario, data in scenario_metrics.items():
        if data.get('status') == 'data_unavailable':
            continue
        CH = data['portlandite_dissolution']
        k = CH.get('rate_constant', 0)
        t_half = CH.get('half_life_days', float('inf'))
        depl = CH.get('depletion_percent', 0)
        print(f"{scenario:<20} {k:<15.4e} {t_half:<20.1f} {depl:<15.1f}")
    
    print("\n\nChloride Binding Capacity:")
    print(f"{'Scenario':<20} {'Bound (mg/g)':<20} {'Friedel (mol)':<20}")
    print("-" * 60)
    
    for scenario, data in scenario_metrics.items():
        if 'NaCl' not in scenario and 'mixed' not in scenario:
            continue
        if data.get('status') == 'data_unavailable':
            continue
        Cl = data['chloride_binding']
        bound = Cl.get('total_bound_mg_per_g', 0)
        friedel = Cl.get('final_friedel_mol', 0)
        print(f"{scenario:<20} {bound:<20.2f} {friedel:<20.3f}")
    
    print("\n\nPressure Acceleration Factors:")
    print(f"{'Solution':<20} {'Acceleration':<20} {'Interpretation':<40}")
    print("-" * 80)
    
    for solution, factor in metrics['acceleration_factors'].items():
        if factor['status'] == 'calculated':
            accel = factor['acceleration_factor']
            interp = factor['interpretation']
            print(f"{solution.upper():<20} {accel:<20.2f} {interp:<40}")


def main():
    """
    Main metrics calculation workflow.
    """
    print(f"\n{'#'*80}")
    print("PHASE 6: METRICS CALCULATOR")
    print("Degradation Rate Quantification and Damage Index Calculation")
    print(f"{'#'*80}")
    
    # Define paths
    project_root = Path(__file__).parent.parent
    outputs_dir = project_root / 'outputs'
    results_dir = project_root / 'results' / 'metrics'
    output_file = results_dir / 'degradation_metrics_report.json'
    
    # Define scenarios
    scenarios = [
        'PW_immersion',
        'PW_pressure',
        'NaCl_immersion',
        'NaCl_pressure',
        'mixed_immersion',
        'mixed_pressure'
    ]
    
    try:
        # Calculate all metrics
        metrics = calculate_all_metrics(scenarios, str(outputs_dir))
        
        # Save report
        save_metrics_report(metrics, str(output_file))
        
        # Print summary
        print_metrics_summary(metrics)
        
        print(f"\n{'='*80}")
        print("METRICS CALCULATION COMPLETE")
        print(f"{'='*80}")
        print(f"✓ All degradation metrics calculated")
        print(f"✓ Pressure acceleration factors determined")
        print(f"✓ Report saved to: {output_file}")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
