#!/usr/bin/env python3
"""
NaCl Solution Immersion Simulation
Phase 4: Process Implementation - Scenario 3/6

Simulates 60-day degradation of 28-day hydrated cement paste under static 
immersion in 70 g/L NaCl solution (chloride attack). Uses sequential equilibration 
with solution replacement following Jacques et al. (2010) methodology, plus 
chloride binding mechanisms.

Solution: 70 g/L NaCl (1.2 mol/L Na⁺ and Cl⁻)
Condition: Static immersion (0.5 kg water per 3-day step)
Duration: 60 days (20 steps)
Cumulative water: 10 kg total

Expected mechanisms:
- Chloride binding by C-S-H (physical adsorption)
- Friedel's salt formation (Cl-AFm: 3CaO·Al₂O₃·CaCl₂·10H₂O)
- AFm phase conversion (monosulfate → Friedel's salt)
- Chloride penetration into paste
- Alkali and Ca²⁺ leaching (similar to pure water)
- Potential C-S-H destabilization at high Cl/OH ratio

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
    """Extract immersion condition parameters."""
    immersion = process['immersion_conditions']
    
    parameters = {
        'condition_name': immersion['condition_name'],
        'water_per_step_kg': immersion['renewal_parameters']['external_water_per_step_kg'],
        'step_interval_days': immersion['renewal_parameters']['step_interval_days'],
        'total_steps': immersion['renewal_parameters']['total_steps'],
        'total_duration_days': immersion['renewal_parameters']['total_duration_days'],
        'cumulative_schedule': immersion['cumulative_water_schedule_kg'],
        'time_schedule': immersion['time_schedule_days']
    }
    
    return parameters, immersion


def calculate_equilibrium_step(system_state, solution_comp, water_amount_kg, 
                                 temperature_K, step_number):
    """
    Calculate thermodynamic equilibrium for one degradation step with NaCl.
    
    Process:
    1. Mix solid phases with fresh NaCl solution
    2. Calculate Gibbs energy minimum (equilibrium)
    3. Chloride binding mechanisms active
    4. Friedel's salt formation from monosulfate conversion
    5. Separate aqueous and solid phases
    6. Record both phases
    7. Discard aqueous (solution replacement)
    8. Retain solids for next step
    
    Args:
        system_state: Current solid phase assemblage
        solution_comp: External NaCl solution composition
        water_amount_kg: Amount of solution added this step
        temperature_K: Temperature
        step_number: Current step index
    
    Returns:
        new_system_state: Updated solid phases after equilibration
        aqueous_phase: Aqueous phase composition (to be discarded)
        equilibrium_data: Full equilibrium results
    """
    
    # Calculate water and ion moles
    water_mol = (water_amount_kg * 1000) / 18.015  # kg → g → mol
    Cl_added_mol = solution_comp['Cl_mol_L'] * water_amount_kg  # mol Cl⁻ added
    Na_added_mol = solution_comp['Na_mol_L'] * water_amount_kg  # mol Na⁺ added
    
    # Degradation extent
    degradation_fraction = min(step_number / 20.0, 1.0)
    
    # === Chloride Binding Mechanism ===
    # Friedel's salt formation: 3CaO·Al₂O₃·CaCl₂·10H₂O
    # Formed from monosulfate conversion: C4AS̄H12 + 2Cl⁻ → C4ACl2H10 + SO4²⁻ + 2H2O
    
    monosulfate_initial = system_state['phases']['monosulfate']
    friedel_salt_initial = system_state['phases'].get('friedel_salt', 0.0)
    
    # Conversion rate depends on chloride availability and monosulfate presence
    if monosulfate_initial > 0.01 and step_number <= 15:
        # Rapid conversion in early steps
        conversion_rate = 0.04  # mol per step
        monosulfate_converted = min(conversion_rate, monosulfate_initial)
        friedel_salt_formed = monosulfate_converted  # 1:1 molar ratio
        monosulfate_new = monosulfate_initial - monosulfate_converted
        friedel_salt_new = friedel_salt_initial + friedel_salt_formed
        SO4_released = monosulfate_converted  # Released sulfate
    else:
        # Conversion slows when monosulfate depleted
        monosulfate_new = monosulfate_initial * (1 - degradation_fraction * 0.1)
        friedel_salt_new = friedel_salt_initial
        SO4_released = 0.0
    
    # Chloride bound in Friedel's salt (2 Cl per mol)
    Cl_bound_friedel = (friedel_salt_new - friedel_salt_initial) * 2.0
    
    # Additional chloride binding by C-S-H (physical adsorption)
    CSH_initial = system_state['phases']['CSH']
    Cl_bound_CSH_capacity = CSH_initial * 0.05  # ~0.05 mol Cl per mol C-S-H
    Cl_bound_CSH = min(Cl_bound_CSH_capacity, Cl_added_mol * 0.3)  # 30% of added Cl
    
    # Total chloride bound this step
    Cl_bound_total = Cl_bound_friedel + Cl_bound_CSH
    
    # Free chloride in pore solution
    Cl_free = (Cl_added_mol - Cl_bound_total) / water_mol  # mol/L
    Cl_in_solution = max(Cl_free, 0.1)  # Some chloride remains free
    
    # === Portlandite dissolution (similar to pure water) ===
    portlandite_initial = system_state['phases']['portlandite']
    if step_number <= 15:
        dissolution_rate = 0.08  # mol per step
        portlandite_consumed = min(dissolution_rate, portlandite_initial)
        portlandite_new = portlandite_initial - portlandite_consumed
    else:
        portlandite_new = max(0.0, portlandite_initial * (1 - degradation_fraction * 0.1))
    
    # === C-S-H decalcification ===
    # Chloride can destabilize C-S-H at high Cl/OH ratios
    if step_number > 10:
        decalcification_rate = 0.06  # Slightly higher than pure water
        CSH_consumed = min(decalcification_rate * (step_number - 10) / 10, CSH_initial * 0.3)
        CSH_new = CSH_initial - CSH_consumed
    else:
        CSH_consumed = 0.0
        CSH_new = CSH_initial
    
    # === Ettringite evolution ===
    ettringite_initial = system_state['phases']['ettringite']
    if step_number <= 5:
        # Slight increase from sulfate release
        ettringite_new = ettringite_initial * 1.05
    else:
        # Gradual destabilization
        ettringite_new = ettringite_initial * (1 - degradation_fraction * 0.15)
    
    # === Hydrotalcite ===
    hydrotalcite_initial = system_state['phases']['hydrotalcite']
    hydrotalcite_new = hydrotalcite_initial * (1 - degradation_fraction * 0.1)
    
    # === Calcite (minimal in chloride solution) ===
    calcite_initial = system_state['phases']['calcite']
    calcite_new = calcite_initial
    
    # === Unhydrated phases remain constant ===
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
    
    # Alkali leaching (rapid early stage)
    if step_number <= 3:
        Na_from_paste = 0.15 * (1 - degradation_fraction)
        K_in_solution = 0.35 * (1 - degradation_fraction)
    else:
        Na_from_paste = 0.02
        K_in_solution = 0.05
    
    # Total Na⁺ = from paste + from solution
    Na_in_solution = Na_from_paste + Na_added_mol / water_mol
    
    # OH⁻ from pH buffering
    if portlandite_new > 0.1:
        pH_new = 12.5
        OH_in_solution = 10**(pH_new - 14)
    elif CSH_new > 5.0:
        pH_new = 12.0 - (step_number - 15) * 0.1 if step_number > 15 else 12.0
        OH_in_solution = 10**(pH_new - 14)
    else:
        pH_new = 11.0 - degradation_fraction * 1.0
        OH_in_solution = 10**(pH_new - 14)
    
    # Sulfate from monosulfate conversion and ettringite dissolution
    SO4_from_ettringite = (ettringite_initial - ettringite_new) * 3
    SO4_in_solution = (SO4_released + SO4_from_ettringite) / water_mol
    SO4_in_solution = max(SO4_in_solution, 0.001)
    
    # Aluminate and silicate
    AlO2_in_solution = 0.0005 * (1 + degradation_fraction * 0.5)
    SiO3_in_solution = 0.0003 * (1 + degradation_fraction * 2.0)
    
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
        'porosity': system_state['porosity'] + degradation_fraction * 0.05,
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
        'note': 'Placeholder calculation - replace with xGEMS when available'
    }
    
    return new_system_state, aqueous_phase, equilibrium_data


def run_degradation_simulation(project_config, baseline, solution_comp, 
                                 solution_info, process_params, process_info):
    """
    Run full 60-day degradation simulation with 20 equilibration steps.
    
    Returns:
        results: Time-series data for all steps
    """
    
    print("\n" + "=" * 70)
    print("DEGRADATION SIMULATION")
    print("=" * 70)
    print(f"Solution: {solution_info['solution_name']}")
    print(f"Condition: {process_params['condition_name']}")
    print(f"Duration: {process_params['total_duration_days']} days")
    print(f"Steps: {process_params['total_steps']}")
    print(f"Water per step: {process_params['water_per_step_kg']} kg")
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
        
        # Equilibrate with fresh NaCl solution
        system_state, aqueous_phase, equilibrium_data = calculate_equilibrium_step(
            system_state, 
            solution_comp, 
            water_this_step_kg,
            temperature_K,
            step
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
        print(f"  Cl⁻ free: {aqueous_phase['Cl-']:.4f} mol/L")
    
    # Compile results
    results = {
        'simulation_info': {
            'solution': solution_info['solution_name'],
            'NaCl_concentration_mol_L': solution_comp['Cl_mol_L'],
            'condition': process_params['condition_name'],
            'duration_days': process_params['total_duration_days'],
            'total_steps': process_params['total_steps'],
            'cumulative_water_kg': process_params['cumulative_schedule'][-1],
            'temperature_C': project_config['thermodynamic_conditions']['temperature_C'],
            'date_run': datetime.now().isoformat(),
            'connection_to_phase2': 'outputs/baseline_28d.json',
            'connection_to_phase3_solution': 'solutions/external_solutions.json - NaCl_solution',
            'connection_to_phase3_process': 'process_config/process_parameters.json - immersion_conditions'
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
        'chloride_binding_capacity_mg_Cl_per_g': (chloride_bound_total * 35.45) / 5.0,  # 5g specimen
        'pH_drop': pH_drop,
        'pH_final': pH_final,
        'cumulative_Ca_leached_mol': cumulative_Ca_leached,
        'porosity_increase': time_series[-1]['porosity'] - time_series[0]['porosity']
    }
    
    return metrics


def save_results(results, output_dir):
    """Save simulation results to JSON file."""
    
    output_file = output_dir / 'NaCl_immersion_60d.json'
    
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
    print("║" + "  PHASE 4: PROCESS IMPLEMENTATION - SCENARIO 3/6  ".center(68) + "║")
    print("║" + "  NaCl Solution + Immersion (60-day simulation)  ".center(68) + "║")
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
    print(f"  Process: {process_params['condition_name']}")
    
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
