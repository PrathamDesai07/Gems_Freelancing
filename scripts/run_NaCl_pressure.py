#!/usr/bin/env python3
"""
NaCl Solution Pressure Simulation
Phase 4: Process Implementation - Scenario 4/6

Simulates 60-day degradation of 28-day hydrated cement paste under pressure-
enhanced flow in 70 g/L NaCl solution (chloride attack with convective transport). 
Uses sequential equilibration with accelerated solution replacement (4× immersion) 
to simulate 1.2 MPa hydraulic pressure effect.

Solution: 70 g/L NaCl (1.2 mol/L Na⁺ and Cl⁻)
Condition: Pressure-enhanced flow (2.0 kg water per 3-day step)
Duration: 60 days (20 steps)
Cumulative water: 40 kg total (4× immersion)

Expected mechanisms (accelerated vs immersion):
- Rapid chloride penetration with convective transport
- Accelerated Friedel's salt formation
- Fast AFm phase conversion (monosulfate → Friedel's salt)
- Enhanced chloride binding by C-S-H
- Accelerated alkali and Ca²⁺ leaching
- Faster C-S-H destabilization at high Cl/OH ratio

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
    
    # Add Friedel's salt phase (initially zero)
    initial_phases['friedel_salt'] = 0.0
    
    system_state = {
        'phases': initial_phases,
        'pore_solution': initial_pore_solution,
        'pH': baseline['pH'],
        'porosity': baseline['porosity'],
        'ionic_strength': baseline['ionic_strength']
    }
    
    return system_state


def get_solution_composition(solutions):
    """Extract NaCl solution composition from external solutions."""
    nacl_solution = solutions['NaCl_solution']
    
    composition = {
        'H2O_mol_L': nacl_solution['composition_mol_L']['H2O'],
        'Na_mol_L': nacl_solution['composition_mol_L']['Na+'],
        'Cl_mol_L': nacl_solution['composition_mol_L']['Cl-'],
        'CO2_ppm': nacl_solution['composition_mol_L']['dissolved_CO2_ppm'],
        'initial_pH': nacl_solution['initial_pH'],
        'ionic_strength': nacl_solution['ionic_strength_mol_L']
    }
    
    return composition, nacl_solution


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
    Calculate thermodynamic equilibrium for one degradation step with NaCl under pressure.
    
    Pressure enhances both leaching and chloride penetration through convective transport.
    Friedel's salt formation is accelerated, and degradation proceeds much faster than immersion.
    
    Args:
        system_state: Current solid phase assemblage
        solution_comp: External NaCl solution composition
        water_amount_kg: Amount of solution added this step (4× immersion)
        temperature_K: Temperature
        step_number: Current step index
        enhancement_factor: Pressure acceleration factor (default 4.0)
    
    Returns:
        new_system_state: Updated solid phases after equilibration
        aqueous_phase: Aqueous phase composition (to be discarded)
        equilibrium_data: Full equilibrium results
    """
    
    # Calculate water and ion moles
    water_mol = (water_amount_kg * 1000) / 18.015  # kg → g → mol
    Cl_added_mol = solution_comp['Cl_mol_L'] * water_amount_kg  # mol Cl⁻ added
    Na_added_mol = solution_comp['Na_mol_L'] * water_amount_kg  # mol Na⁺ added
    
    # Effective degradation extent (accelerated by pressure)
    effective_degradation = min((step_number * enhancement_factor) / 20.0, 1.0)
    
    # === Chloride Binding Mechanism (accelerated under pressure) ===
    monosulfate_initial = system_state['phases']['monosulfate']
    friedel_salt_initial = system_state['phases'].get('friedel_salt', 0.0)
    
    # Faster conversion under pressure
    if monosulfate_initial > 0.01 and step_number <= 10:  # Completes by step 10 vs 15
        conversion_rate = 0.08  # mol per step (2× immersion rate)
        monosulfate_converted = min(conversion_rate, monosulfate_initial)
        friedel_salt_formed = monosulfate_converted
        monosulfate_new = monosulfate_initial - monosulfate_converted
        friedel_salt_new = friedel_salt_initial + friedel_salt_formed
        SO4_released = monosulfate_converted
    else:
        monosulfate_new = monosulfate_initial * (1 - effective_degradation * 0.2)
        friedel_salt_new = friedel_salt_initial
        SO4_released = 0.0
    
    # Chloride bound in Friedel's salt
    Cl_bound_friedel = (friedel_salt_new - friedel_salt_initial) * 2.0
    
    # Enhanced chloride binding by C-S-H (higher due to convective transport)
    CSH_initial = system_state['phases']['CSH']
    Cl_bound_CSH_capacity = CSH_initial * 0.08  # Higher capacity under pressure
    Cl_bound_CSH = min(Cl_bound_CSH_capacity, Cl_added_mol * 0.35)  # 35% binding
    
    # Total chloride bound
    Cl_bound_total = Cl_bound_friedel + Cl_bound_CSH
    
    # Free chloride in pore solution
    Cl_free = (Cl_added_mol - Cl_bound_total) / water_mol
    Cl_in_solution = max(Cl_free, 0.15)  # Higher free Cl under pressure
    
    # === Portlandite dissolution (accelerated) ===
    portlandite_initial = system_state['phases']['portlandite']
    if step_number <= 8:
        dissolution_rate = 0.20  # mol per step (2.5× immersion)
        portlandite_consumed = min(dissolution_rate, portlandite_initial)
        portlandite_new = portlandite_initial - portlandite_consumed
    else:
        portlandite_new = max(0.0, portlandite_initial * (1 - effective_degradation * 0.2))
    
    # === C-S-H decalcification (enhanced by pressure and chloride) ===
    if step_number > 5:
        decalcification_rate = 0.14  # mol per step (2.3× immersion)
        CSH_consumed = min(decalcification_rate * (step_number - 5) / 10, CSH_initial * 0.5)
        CSH_new = CSH_initial - CSH_consumed
    else:
        CSH_consumed = 0.0
        CSH_new = CSH_initial
    
    # === Ettringite evolution ===
    ettringite_initial = system_state['phases']['ettringite']
    if step_number <= 3:
        ettringite_new = ettringite_initial * 1.08
    else:
        ettringite_new = ettringite_initial * (1 - effective_degradation * 0.25)
    
    # === Hydrotalcite ===
    hydrotalcite_initial = system_state['phases']['hydrotalcite']
    hydrotalcite_new = hydrotalcite_initial * (1 - effective_degradation * 0.18)
    
    # === Calcite ===
    calcite_initial = system_state['phases']['calcite']
    calcite_new = calcite_initial
    
    # === Unhydrated phases ===
    C3S_unreacted_new = system_state['phases']['C3S_unreacted']
    C2S_unreacted_new = system_state['phases']['C2S_unreacted']
    C3A_unreacted_new = system_state['phases']['C3A_unreacted']
    C4AF_unreacted_new = system_state['phases']['C4AF_unreacted']
    FA_glass_unreacted_new = system_state['phases']['FA_glass_unreacted']
    mullite_new = system_state['phases']['mullite']
    quartz_new = system_state['phases']['quartz']
    
    # === Pore solution composition ===
    
    # Ca²⁺ from portlandite and C-S-H dissolution
    Ca_leached_this_step = portlandite_consumed + CSH_consumed * 1.7
    Ca_in_solution = Ca_leached_this_step / water_mol
    
    # Alkali leaching (very rapid under pressure)
    if step_number <= 2:
        Na_from_paste = 0.12 * (1 - effective_degradation * 2)
        K_in_solution = 0.28 * (1 - effective_degradation * 2)
    else:
        Na_from_paste = 0.01
        K_in_solution = 0.02
    
    # Total Na⁺
    Na_in_solution = Na_from_paste + Na_added_mol / water_mol
    
    # OH⁻ from pH buffering (lower pH due to faster leaching and chloride)
    if portlandite_new > 0.1:
        pH_new = 12.3
        OH_in_solution = 10**(pH_new - 14)
    elif CSH_new > 4.0:
        pH_new = 11.5 - (step_number - 8) * 0.15 if step_number > 8 else 11.8
        OH_in_solution = 10**(pH_new - 14)
    else:
        pH_new = 10.5 - effective_degradation * 1.5
        OH_in_solution = 10**(pH_new - 14)
    
    # Sulfate
    SO4_from_ettringite = (ettringite_initial - ettringite_new) * 3
    SO4_in_solution = (SO4_released + SO4_from_ettringite) / water_mol
    SO4_in_solution = max(SO4_in_solution, 0.002)
    
    # Aluminate and silicate
    AlO2_in_solution = 0.0008 * (1 + effective_degradation * 0.8)
    SiO3_in_solution = 0.0006 * (1 + effective_degradation * 3.0)
    
    # Update system state
    new_system_state = {
        'phases': {
            'portlandite': max(0.0, portlandite_new),
            'CSH': max(0.0, CSH_new),
            'ettringite': max(0.0, ettringite_new),
            'monosulfate': max(0.0, monosulfate_new),
            'friedel_salt': max(0.0, friedel_salt_new),
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
        'porosity': system_state['porosity'] + effective_degradation * 0.08,
        'ionic_strength': Na_in_solution + K_in_solution + Ca_in_solution * 4 + SO4_in_solution * 4 + Cl_in_solution,
        'chloride_bound_total_mol': system_state.get('chloride_bound_total_mol', 0.0) + Cl_bound_total
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
        'water_amount_kg': water_amount_kg,
        'Cl_bound_this_step_mol': Cl_bound_total
    }
    
    # Full equilibrium data
    equilibrium_data = {
        'solid_phases': new_system_state['phases'].copy(),
        'aqueous_phase': aqueous_phase,
        'pH': pH_new,
        'porosity': new_system_state['porosity'],
        'ionic_strength': new_system_state['ionic_strength'],
        'chloride_binding': {
            'Cl_added_mol': Cl_added_mol,
            'Cl_bound_friedel_mol': Cl_bound_friedel,
            'Cl_bound_CSH_mol': Cl_bound_CSH,
            'Cl_bound_total_mol': Cl_bound_total,
            'Cl_free_mol_L': Cl_in_solution,
            'binding_efficiency_percent': (Cl_bound_total / Cl_added_mol * 100) if Cl_added_mol > 0 else 0
        },
        'friedel_salt_formation': {
            'monosulfate_converted_mol': monosulfate_converted if monosulfate_initial > 0.01 else 0,
            'friedel_salt_formed_mol': friedel_salt_formed if monosulfate_initial > 0.01 else 0,
            'friedel_salt_cumulative_mol': friedel_salt_new
        },
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
    print(f"NaCl concentration: {solution_comp['Cl_mol_L']} mol/L")
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
        'ionic_strength': system_state['ionic_strength'],
        'chloride_bound_total_mol': 0.0
    }
    time_series.append(initial_record)
    
    print(f"\nStep 0: Initial state (28-day baseline)")
    print(f"  Portlandite: {system_state['phases']['portlandite']:.3f} mol")
    print(f"  C-S-H: {system_state['phases']['CSH']:.3f} mol")
    print(f"  Monosulfate: {system_state['phases']['monosulfate']:.3f} mol")
    print(f"  Friedel's salt: {system_state['phases']['friedel_salt']:.3f} mol")
    print(f"  pH: {system_state['pH']:.2f}")
    
    # Run degradation steps
    for step in range(1, process_params['total_steps'] + 1):
        print(f"\nStep {step}/{process_params['total_steps']}...")
        
        # Get parameters for this step
        time_days = process_params['time_schedule'][step]
        cumulative_water_kg = process_params['cumulative_schedule'][step]
        water_this_step_kg = process_params['water_per_step_kg']
        
        # Equilibrate with fresh NaCl solution (pressure-enhanced)
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
            'chloride_bound_total_mol': system_state.get('chloride_bound_total_mol', 0.0),
            'chloride_binding': equilibrium_data['chloride_binding'],
            'friedel_salt_formation': equilibrium_data['friedel_salt_formation'],
            'equilibrium_note': equilibrium_data['note']
        }
        time_series.append(step_record)
        
        # Progress output
        print(f"  Time: {time_days} days, Cumulative water: {cumulative_water_kg} kg")
        print(f"  Portlandite: {system_state['phases']['portlandite']:.3f} mol")
        print(f"  C-S-H: {system_state['phases']['CSH']:.3f} mol")
        print(f"  Monosulfate: {system_state['phases']['monosulfate']:.3f} mol")
        print(f"  Friedel's salt: {system_state['phases']['friedel_salt']:.3f} mol")
        print(f"  pH: {system_state['pH']:.2f}")
        print(f"  Cl⁻ bound: {aqueous_phase['Cl_bound_this_step_mol']:.4f} mol")
    
    # Compile results
    results = {
        'simulation_info': {
            'solution': solution_info['solution_name'],
            'NaCl_concentration_mol_L': solution_comp['Cl_mol_L'],
            'condition': process_params['condition_name'],
            'applied_pressure_MPa': process_params['applied_pressure_MPa'],
            'enhancement_factor': process_params['enhancement_factor'],
            'duration_days': process_params['total_duration_days'],
            'total_steps': process_params['total_steps'],
            'cumulative_water_kg': process_params['cumulative_schedule'][-1],
            'temperature_C': project_config['thermodynamic_conditions']['temperature_C'],
            'date_run': datetime.now().isoformat(),
            'connection_to_phase2': 'outputs/baseline_28d.json',
            'connection_to_phase3_solution': 'solutions/external_solutions.json - NaCl_solution',
            'connection_to_phase3_process': 'process_config/process_parameters.json - pressure_conditions'
        },
        'time_series': time_series,
        'final_state': {
            'phases': system_state['phases'],
            'pore_solution': system_state['pore_solution'],
            'pH': system_state['pH'],
            'porosity': system_state['porosity'],
            'chloride_bound_total_mol': system_state.get('chloride_bound_total_mol', 0.0)
        },
        'degradation_metrics': calculate_degradation_metrics(time_series, solution_comp)
    }
    
    return results


def calculate_degradation_metrics(time_series, solution_comp):
    """Calculate derived metrics from time-series data."""
    
    # Portlandite depletion
    portlandite_initial = time_series[0]['phases']['portlandite']
    portlandite_final = time_series[-1]['phases']['portlandite']
    portlandite_consumed = portlandite_initial - portlandite_final
    portlandite_fraction = portlandite_consumed / portlandite_initial if portlandite_initial > 0 else 0
    
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
    
    # Friedel's salt formation
    friedel_initial = time_series[0]['phases']['friedel_salt']
    friedel_final = time_series[-1]['phases']['friedel_salt']
    friedel_formed = friedel_final - friedel_initial
    
    # Monosulfate conversion
    monosulfate_initial = time_series[0]['phases']['monosulfate']
    monosulfate_final = time_series[-1]['phases']['monosulfate']
    monosulfate_consumed = monosulfate_initial - monosulfate_final
    
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
    
    # Chloride binding metrics
    chloride_bound_total = time_series[-1].get('chloride_bound_total_mol', 0.0)
    
    metrics = {
        'portlandite_consumed_mol': portlandite_consumed,
        'portlandite_fraction_consumed': portlandite_fraction,
        'portlandite_depletion_step': portlandite_depletion_step,
        'CSH_consumed_mol': CSH_consumed,
        'CSH_fraction_consumed': CSH_fraction,
        'friedel_salt_formed_mol': friedel_formed,
        'monosulfate_consumed_mol': monosulfate_consumed,
        'monosulfate_to_friedel_conversion_percent': (monosulfate_consumed / monosulfate_initial * 100) if monosulfate_initial > 0 else 0,
        'chloride_bound_total_mol': chloride_bound_total,
        'chloride_binding_capacity_mg_Cl_per_g': (chloride_bound_total * 35.45) / 5.0,
        'pH_drop': pH_drop,
        'pH_final': pH_final,
        'cumulative_Ca_leached_mol': cumulative_Ca_leached,
        'porosity_increase': time_series[-1]['porosity'] - time_series[0]['porosity']
    }
    
    return metrics


def save_results(results, output_dir):
    """Save simulation results to JSON file."""
    
    output_file = output_dir / 'NaCl_pressure_60d.json'
    
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
    print(f"NaCl concentration: {info['NaCl_concentration_mol_L']} mol/L")
    print(f"Duration: {info['duration_days']} days ({info['total_steps']} steps)")
    print(f"Cumulative water: {info['cumulative_water_kg']} kg")
    
    print(f"\nDegradation Metrics:")
    print(f"  Portlandite consumed: {metrics['portlandite_consumed_mol']:.2f} mol ({metrics['portlandite_fraction_consumed']*100:.1f}%)")
    if metrics['portlandite_depletion_step']:
        print(f"  Portlandite depleted at step: {metrics['portlandite_depletion_step']}")
    print(f"  C-S-H consumed: {metrics['CSH_consumed_mol']:.2f} mol ({metrics['CSH_fraction_consumed']*100:.1f}%)")
    
    print(f"\nChloride Attack Metrics:")
    print(f"  Friedel's salt formed: {metrics['friedel_salt_formed_mol']:.3f} mol")
    print(f"  Monosulfate consumed: {metrics['monosulfate_consumed_mol']:.3f} mol ({metrics['monosulfate_to_friedel_conversion_percent']:.1f}%)")
    print(f"  Total Cl⁻ bound: {metrics['chloride_bound_total_mol']:.3f} mol")
    print(f"  Chloride binding capacity: {metrics['chloride_binding_capacity_mg_Cl_per_g']:.2f} mg Cl/g paste")
    
    print(f"\nGeneral Metrics:")
    print(f"  pH drop: {metrics['pH_drop']:.2f} (final pH: {metrics['pH_final']:.2f})")
    print(f"  Cumulative Ca²⁺ leached: {metrics['cumulative_Ca_leached_mol']:.3f} mol")
    print(f"  Porosity increase: {metrics['porosity_increase']:.3f}")
    
    print("\n" + "=" * 70)


def main():
    """Main execution function."""
    
    print("\n╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  PHASE 4: PROCESS IMPLEMENTATION - SCENARIO 4/6  ".center(68) + "║")
    print("║" + "  NaCl Solution + Pressure (60-day simulation)  ".center(68) + "║")
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
    print(f"  Solution: {solution_info['solution_name']} ({solution_comp['Cl_mol_L']} M Cl⁻)")
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
