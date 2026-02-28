#!/usr/bin/env python3
"""
Pure Water Pressure Simulation
Phase 4: Process Implementation - Scenario 2/6

Simulates 60-day degradation of 28-day hydrated cement paste under pressure-
enhanced flow in pure water. Uses sequential equilibration with accelerated 
solution replacement (4× water compared to immersion) to simulate 1.2 MPa 
hydraulic pressure effect.

Solution: Pure deionized water (CO2-free)
Condition: Pressure-enhanced flow (2.0 kg water per 3-day step)
Duration: 60 days (20 steps)
Cumulative water: 40 kg total (4× immersion)

Expected mechanisms (accelerated vs immersion):
- Faster alkali (Na, K) leaching from pore solution
- Accelerated portlandite dissolution and Ca²⁺ leaching
- Enhanced C-S-H decalcification through convective transport
- Rapid AFm/AFt phase destabilization
- Steeper pH gradient development

Project: Multi-environment reaction-transport modeling of fly ash blended cement paste
Date: February 2026
"""

import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime


def load_configurations():
    """Load all required configuration files from Phases 1-3."""
    base_path = Path(__file__).parent.parent
    
    print("Loading configurations...")
    
    # Phase 1: Thermodynamic basis
    with open(base_path / 'gems_project' / 'project_config.json', 'r') as f:
        project_config = json.load(f)
    print(f"  ✓ Phase 1: {project_config['project_name']}")
    
    # Phase 2: Baseline 28-day hydrated state
    with open(base_path / 'outputs' / 'baseline_28d.json', 'r') as f:
        baseline = json.load(f)
    print(f"  ✓ Phase 2: Baseline 28-day state loaded")
    
    # Phase 3: External solutions
    with open(base_path / 'solutions' / 'external_solutions.json', 'r') as f:
        solutions = json.load(f)
    print(f"  ✓ Phase 3: External solutions loaded")
    
    # Phase 3: Process parameters
    with open(base_path / 'process_config' / 'process_parameters.json', 'r') as f:
        process = json.load(f)
    print(f"  ✓ Phase 3: Process parameters loaded")
    
    return project_config, baseline, solutions, process


def initialize_system_state(baseline):
    """
    Initialize solid phase assemblage and pore solution from 28-day baseline.
    This is the starting point before any degradation.
    """
    # Deep copy of baseline state to avoid modifying the original
    initial_phases = baseline['phases'].copy()
    initial_pore_solution = baseline['pore_solution'].copy()
    
    system_state = {
        'phases': initial_phases,
        'pore_solution': initial_pore_solution,
        'pH': baseline['pH'],
        'porosity': baseline['porosity'],
        'ionic_strength': baseline['ionic_strength']
    }
    
    return system_state


def get_solution_composition(solutions):
    """Extract pure water composition from external solutions."""
    pw_solution = solutions['pure_water']
    
    composition = {
        'H2O_mol_L': pw_solution['composition_mol_L']['H2O'],
        'CO2_ppm': pw_solution['composition_mol_L']['dissolved_CO2_ppm'],
        'initial_pH': pw_solution['initial_pH'],
        'ionic_strength': pw_solution['ionic_strength_mol_L']
    }
    
    return composition, pw_solution


def get_process_parameters(process):
    """Extract pressure condition parameters."""
    pressure = process['pressure_conditions']
    
    parameters = {
        'condition_name': pressure['condition_name'],
        'applied_pressure_MPa': pressure['applied_pressure_MPa'],
        'water_per_step_kg': pressure['renewal_parameters']['external_water_per_step_kg'],
        'step_interval_days': pressure['renewal_parameters']['step_interval_days'],
        'total_steps': pressure['renewal_parameters']['total_steps'],
        'total_duration_days': pressure['renewal_parameters']['total_duration_days'],
        'cumulative_schedule': pressure['cumulative_water_schedule_kg'],
        'time_schedule': pressure['time_schedule_days'],
        'enhancement_factor': pressure['physical_interpretation']['pressure_effect']
    }
    
    return parameters, pressure


def calculate_equilibrium_step(system_state, solution_comp, water_amount_kg, 
                                 temperature_K, step_number, enhancement_factor=4.0):
    """
    Calculate thermodynamic equilibrium for one degradation step under pressure.
    
    The pressure effect is modeled through enhanced solution renewal rate,
    representing convection-enhanced mass transfer. Degradation proceeds faster
    than immersion due to increased water-paste contact.
    
    Args:
        system_state: Current solid phase assemblage
        solution_comp: External solution composition
        water_amount_kg: Amount of solution added this step (4× immersion)
        temperature_K: Temperature
        step_number: Current step index
        enhancement_factor: Pressure acceleration factor (default 4.0)
    
    Returns:
        new_system_state: Updated solid phases after equilibration
        aqueous_phase: Aqueous phase composition (to be discarded)
        equilibrium_data: Full equilibrium results
    """
    
    # Calculate water moles
    water_mol = (water_amount_kg * 1000) / 18.015  # kg → g → mol
    
    # Effective degradation extent (accelerated by pressure)
    # Pressure causes faster degradation, so use higher effective step number
    effective_degradation = min((step_number * enhancement_factor) / 20.0, 1.0)
    
    # Portlandite dissolution (much faster under pressure)
    portlandite_initial = system_state['phases']['portlandite']
    if step_number <= 8:  # Depletes by step 8 instead of 15
        # Accelerated dissolution rate
        dissolution_rate = 0.20  # mol per step (2.5× immersion rate)
        portlandite_consumed = min(dissolution_rate, portlandite_initial)
        portlandite_new = portlandite_initial - portlandite_consumed
    else:
        # Portlandite depleted earlier under pressure
        portlandite_new = max(0.0, portlandite_initial * (1 - effective_degradation * 0.2))
    
    # C-S-H decalcification (starts earlier and proceeds faster)
    CSH_initial = system_state['phases']['CSH']
    if step_number > 5:  # Starts at step 5 instead of 10
        # Accelerated decalcification
        decalcification_rate = 0.12  # mol per step (2.4× immersion)
        CSH_consumed = min(decalcification_rate * (step_number - 5) / 10, CSH_initial * 0.45)
        CSH_new = CSH_initial - CSH_consumed
    else:
        CSH_new = CSH_initial
    
    # Ettringite evolution (faster cycling)
    ettringite_initial = system_state['phases']['ettringite']
    if step_number <= 3:
        ettringite_new = ettringite_initial * 1.08
    else:
        ettringite_new = ettringite_initial * (1 - effective_degradation * 0.25)
    
    # Monosulfate destabilization (faster)
    monosulfate_initial = system_state['phases']['monosulfate']
    monosulfate_new = monosulfate_initial * (1 - effective_degradation * 0.45)
    
    # Hydrotalcite dissolution (enhanced)
    hydrotalcite_initial = system_state['phases']['hydrotalcite']
    hydrotalcite_new = hydrotalcite_initial * (1 - effective_degradation * 0.18)
    
    # Calcite formation minimal (CO2-free water)
    calcite_initial = system_state['phases']['calcite']
    calcite_new = calcite_initial
    
    # Unhydrated phases remain constant
    C3S_unreacted_new = system_state['phases']['C3S_unreacted']
    C2S_unreacted_new = system_state['phases']['C2S_unreacted']
    C3A_unreacted_new = system_state['phases']['C3A_unreacted']
    C4AF_unreacted_new = system_state['phases']['C4AF_unreacted']
    FA_glass_unreacted_new = system_state['phases']['FA_glass_unreacted']
    mullite_new = system_state['phases']['mullite']
    quartz_new = system_state['phases']['quartz']
    
    # Calculate pore solution composition after equilibration
    # Higher leaching rates due to pressure-enhanced flow
    
    # Ca²⁺ from portlandite and C-S-H dissolution (higher concentration)
    Ca_leached_this_step = portlandite_consumed + CSH_consumed * 1.7
    Ca_in_solution = Ca_leached_this_step / water_mol  # mol/L
    
    # Alkali leaching (very rapid under pressure, depleted by step 2)
    if step_number <= 2:
        # Stage 1: Very rapid alkali leaching
        Na_in_solution = 0.12 * (1 - effective_degradation * 2)
        K_in_solution = 0.28 * (1 - effective_degradation * 2)
    else:
        # Alkalis almost completely stripped
        Na_in_solution = 0.01
        K_in_solution = 0.02
    
    # OH⁻ from pH buffering (lower pH due to faster leaching)
    if portlandite_new > 0.1:
        # Portlandite buffering but lower pH than immersion
        pH_new = 12.3
        OH_in_solution = 10**(pH_new - 14)
    elif CSH_new > 4.0:
        # C-S-H buffering: pH drops faster
        pH_new = 11.5 - (step_number - 8) * 0.15 if step_number > 8 else 11.8
        OH_in_solution = 10**(pH_new - 14)
    else:
        # Severely degraded: significant pH drop
        pH_new = 10.5 - effective_degradation * 1.5
        OH_in_solution = 10**(pH_new - 14)
    
    # Sulfate from AFm/AFt dissolution (higher)
    SO4_in_solution = (monosulfate_initial - monosulfate_new) / water_mol
    SO4_in_solution += (ettringite_initial - ettringite_new) * 3 / water_mol
    SO4_in_solution = max(SO4_in_solution, 0.002)
    
    # Aluminate and silicate (higher due to C-S-H decalcification)
    AlO2_in_solution = 0.0008 * (1 + effective_degradation * 0.8)
    SiO3_in_solution = 0.0006 * (1 + effective_degradation * 3.0)
    
    # No chloride in pure water
    Cl_in_solution = 0.0
    
    # Update system state
    new_system_state = {
        'phases': {
            'portlandite': max(0.0, portlandite_new),
            'CSH': max(0.0, CSH_new),
            'ettringite': max(0.0, ettringite_new),
            'monosulfate': max(0.0, monosulfate_new),
            'hydrotalcite': max(0.0, hydrotalcite_new),
            'calcite': max(0.0, calcite_new),
            'C3S_unreacted': C3S_unreacted_new,
            'C2S_unreacted': C2S_unreacted_new,
            'C3A_unreacted': C3A_unreacted_new,
            'C4AF_unreacted': C4AF_unreacted_new,
            'FA_glass_unreacted': FA_glass_unreacted_new,
            'mullite': mullite_new,
            'quartz': quartz_new
        },
        'pore_solution': {
            'Ca+2': min(Ca_in_solution, 0.030),
            'Na+': Na_in_solution,
            'K+': K_in_solution,
            'OH-': OH_in_solution,
            'SO4-2': SO4_in_solution,
            'AlO2-': AlO2_in_solution,
            'SiO3-2': SiO3_in_solution,
            'Cl-': Cl_in_solution
        },
        'pH': pH_new,
        'porosity': system_state['porosity'] + effective_degradation * 0.08,  # Higher increase
        'ionic_strength': Na_in_solution + K_in_solution + Ca_in_solution * 4 + SO4_in_solution * 4
    }
    
    # Aqueous phase to be discarded
    aqueous_phase = {
        'Ca+2': Ca_in_solution,
        'Na+': Na_in_solution,
        'K+': K_in_solution,
        'OH-': OH_in_solution,
        'SO4-2': SO4_in_solution,
        'AlO2-': AlO2_in_solution,
        'SiO3-2': SiO3_in_solution,
        'Cl-': Cl_in_solution,
        'pH': pH_new,
        'water_amount_kg': water_amount_kg
    }
    
    # Full equilibrium data
    equilibrium_data = {
        'solid_phases': new_system_state['phases'].copy(),
        'aqueous_phase': aqueous_phase,
        'pH': pH_new,
        'porosity': new_system_state['porosity'],
        'ionic_strength': new_system_state['ionic_strength'],
        'convergence': 'placeholder',
        'pressure_effect': f'{enhancement_factor}× water contact',
        'note': 'Placeholder calculation - replace with xGEMS when available'
    }
    
    return new_system_state, aqueous_phase, equilibrium_data


def run_degradation_simulation(project_config, baseline, solution_comp, 
                                 solution_info, process_params, process_info):
    """
    Run full 60-day degradation simulation with 20 equilibration steps under pressure.
    
    Returns:
        results: Time-series data for all steps
    """
    
    print("\n" + "=" * 70)
    print("DEGRADATION SIMULATION")
    print("=" * 70)
    print(f"Solution: {solution_info['solution_name']}")
    print(f"Condition: {process_params['condition_name']}")
    print(f"Applied pressure: {process_params['applied_pressure_MPa']} MPa")
    print(f"Duration: {process_params['total_duration_days']} days")
    print(f"Steps: {process_params['total_steps']}")
    print(f"Water per step: {process_params['water_per_step_kg']} kg ({process_params['enhancement_factor']})")
    print(f"Total water: {process_params['cumulative_schedule'][-1]} kg")
    print(f"Temperature: {project_config['thermodynamic_conditions']['temperature_C']}°C")
    print("=" * 70)
    
    # Initialize system from baseline
    system_state = initialize_system_state(baseline)
    temperature_K = project_config['thermodynamic_conditions']['temperature_K']
    
    # Storage for time-series results
    time_series = []
    
    # Record initial state (t=0, before degradation)
    initial_record = {
        'step': 0,
        'time_days': 0.0,
        'cumulative_water_kg': 0.0,
        'phases': system_state['phases'].copy(),
        'pore_solution': system_state['pore_solution'].copy(),
        'pH': system_state['pH'],
        'porosity': system_state['porosity'],
        'ionic_strength': system_state['ionic_strength']
    }
    time_series.append(initial_record)
    
    print(f"\nStep 0: Initial state (28-day baseline)")
    print(f"  Portlandite: {system_state['phases']['portlandite']:.3f} mol")
    print(f"  C-S-H: {system_state['phases']['CSH']:.3f} mol")
    print(f"  pH: {system_state['pH']:.2f}")
    
    # Run degradation steps
    for step in range(1, process_params['total_steps'] + 1):
        print(f"\nStep {step}/{process_params['total_steps']}...")
        
        # Get parameters for this step
        time_days = process_params['time_schedule'][step]
        cumulative_water_kg = process_params['cumulative_schedule'][step]
        water_this_step_kg = process_params['water_per_step_kg']
        
        # Equilibrate with fresh external solution (pressure-enhanced)
        system_state, aqueous_phase, equilibrium_data = calculate_equilibrium_step(
            system_state, 
            solution_comp, 
            water_this_step_kg,
            temperature_K,
            step,
            enhancement_factor=4.0
        )
        
        # Record results
        step_record = {
            'step': step,
            'time_days': time_days,
            'cumulative_water_kg': cumulative_water_kg,
            'phases': system_state['phases'].copy(),
            'pore_solution': system_state['pore_solution'].copy(),
            'aqueous_removed': aqueous_phase,
            'pH': system_state['pH'],
            'porosity': system_state['porosity'],
            'ionic_strength': system_state['ionic_strength'],
            'equilibrium_note': equilibrium_data['note']
        }
        time_series.append(step_record)
        
        # Progress output
        print(f"  Time: {time_days} days, Cumulative water: {cumulative_water_kg} kg")
        print(f"  Portlandite: {system_state['phases']['portlandite']:.3f} mol")
        print(f"  C-S-H: {system_state['phases']['CSH']:.3f} mol")
        print(f"  pH: {system_state['pH']:.2f}")
        print(f"  Ca²⁺ leached: {aqueous_phase['Ca+2']:.4f} mol/L")
    
    # Compile results
    results = {
        'simulation_info': {
            'solution': solution_info['solution_name'],
            'condition': process_params['condition_name'],
            'applied_pressure_MPa': process_params['applied_pressure_MPa'],
            'enhancement_factor': process_params['enhancement_factor'],
            'duration_days': process_params['total_duration_days'],
            'total_steps': process_params['total_steps'],
            'cumulative_water_kg': process_params['cumulative_schedule'][-1],
            'temperature_C': project_config['thermodynamic_conditions']['temperature_C'],
            'date_run': datetime.now().isoformat(),
            'connection_to_phase2': 'outputs/baseline_28d.json',
            'connection_to_phase3_solution': 'solutions/external_solutions.json - pure_water',
            'connection_to_phase3_process': 'process_config/process_parameters.json - pressure_conditions'
        },
        'time_series': time_series,
        'final_state': {
            'phases': system_state['phases'],
            'pore_solution': system_state['pore_solution'],
            'pH': system_state['pH'],
            'porosity': system_state['porosity']
        },
        'degradation_metrics': calculate_degradation_metrics(time_series)
    }
    
    return results


def calculate_degradation_metrics(time_series):
    """Calculate derived metrics from time-series data."""
    
    # Portlandite depletion
    portlandite_initial = time_series[0]['phases']['portlandite']
    portlandite_final = time_series[-1]['phases']['portlandite']
    portlandite_consumed = portlandite_initial - portlandite_final
    portlandite_fraction = portlandite_consumed / portlandite_initial if portlandite_initial > 0 else 0
    
    # Find step when portlandite < 10% remaining
    portlandite_depletion_step = None
    for record in time_series:
        if record['phases']['portlandite'] < portlandite_initial * 0.1:
            portlandite_depletion_step = record['step']
            break
    
    # C-S-H decalcification
    CSH_initial = time_series[0]['phases']['CSH']
    CSH_final = time_series[-1]['phases']['CSH']
    CSH_consumed = CSH_initial - CSH_final
    CSH_fraction = CSH_consumed / CSH_initial if CSH_initial > 0 else 0
    
    # pH evolution
    pH_initial = time_series[0]['pH']
    pH_final = time_series[-1]['pH']
    pH_drop = pH_initial - pH_final
    
    # Cumulative Ca leached
    cumulative_Ca_leached = sum([
        record.get('aqueous_removed', {}).get('Ca+2', 0) * 
        record.get('aqueous_removed', {}).get('water_amount_kg', 0) * 1000 / 18.015
        for record in time_series if 'aqueous_removed' in record
    ])
    
    metrics = {
        'portlandite_consumed_mol': portlandite_consumed,
        'portlandite_fraction_consumed': portlandite_fraction,
        'portlandite_depletion_step': portlandite_depletion_step,
        'CSH_consumed_mol': CSH_consumed,
        'CSH_fraction_consumed': CSH_fraction,
        'pH_drop': pH_drop,
        'pH_final': pH_final,
        'cumulative_Ca_leached_mol': cumulative_Ca_leached,
        'porosity_increase': time_series[-1]['porosity'] - time_series[0]['porosity']
    }
    
    return metrics


def save_results(results, output_dir):
    """Save simulation results to JSON file."""
    
    output_file = output_dir / 'PW_pressure_60d.json'
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    
    return output_file


def print_summary(results):
    """Print simulation summary."""
    
    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE - SUMMARY")
    print("=" * 70)
    
    info = results['simulation_info']
    metrics = results['degradation_metrics']
    
    print(f"\nScenario: {info['solution']} + {info['condition']}")
    print(f"Pressure: {info['applied_pressure_MPa']} MPa (enhancement: {info['enhancement_factor']})")
    print(f"Duration: {info['duration_days']} days ({info['total_steps']} steps)")
    print(f"Cumulative water: {info['cumulative_water_kg']} kg")
    
    print(f"\nDegradation Metrics:")
    print(f"  Portlandite consumed: {metrics['portlandite_consumed_mol']:.2f} mol ({metrics['portlandite_fraction_consumed']*100:.1f}%)")
    if metrics['portlandite_depletion_step']:
        print(f"  Portlandite depleted at step: {metrics['portlandite_depletion_step']}")
    print(f"  C-S-H consumed: {metrics['CSH_consumed_mol']:.2f} mol ({metrics['CSH_fraction_consumed']*100:.1f}%)")
    print(f"  pH drop: {metrics['pH_drop']:.2f} (final pH: {metrics['pH_final']:.2f})")
    print(f"  Cumulative Ca²⁺ leached: {metrics['cumulative_Ca_leached_mol']:.3f} mol")
    print(f"  Porosity increase: {metrics['porosity_increase']:.3f}")
    
    print("\n" + "=" * 70)


def main():
    """Main execution function."""
    
    print("\n╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  PHASE 4: PROCESS IMPLEMENTATION - SCENARIO 2/6  ".center(68) + "║")
    print("║" + "  Pure Water + Pressure (60-day simulation)  ".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝\n")
    
    # Load configurations from Phases 1-3
    project_config, baseline, solutions, process = load_configurations()
    
    # Extract specific solution and process parameters
    solution_comp, solution_info = get_solution_composition(solutions)
    process_params, process_info = get_process_parameters(process)
    
    print("\n✓ All configurations loaded successfully")
    print(f"  Temperature: {project_config['thermodynamic_conditions']['temperature_C']}°C (consistent across all phases)")
    print(f"  Initial state: 28-day hydrated paste from Phase 2")
    print(f"  Solution: {solution_info['solution_name']}")
    print(f"  Process: {process_params['condition_name']} ({process_params['applied_pressure_MPa']} MPa)")
    
    # Run simulation
    results = run_degradation_simulation(
        project_config, baseline, solution_comp, 
        solution_info, process_params, process_info
    )
    
    # Save results
    base_path = Path(__file__).parent.parent
    output_dir = base_path / 'outputs'
    output_dir.mkdir(exist_ok=True)
    save_results(results, output_dir)
    
    # Print summary
    print_summary(results)
    
    print("\n✓ Simulation complete!")
    print("\nNote: This simulation uses placeholder equilibrium calculations.")
    print("Install xGEMS to enable actual thermodynamic calculations with CEMDATA18.")


if __name__ == "__main__":
    main()
