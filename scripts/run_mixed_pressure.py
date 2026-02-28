#!/usr/bin/env python3
"""
Mixed Salt Solution Pressure Simulation
Phase 4: Process Implementation - Scenario 6/6

Simulates 60-day degradation of 28-day hydrated cement paste under pressure-
enhanced flow in combined 10 g/L Na₂SO₄ + 70 g/L NaCl solution (accelerated 
coupled sulfate-chloride attack). Uses sequential equilibration with accelerated 
solution replacement (4× immersion) to simulate 1.2 MPa hydraulic pressure effect.

Solution: 10 g/L Na₂SO₄ + 70 g/L NaCl (1.34 M Na⁺, 1.2 M Cl⁻, 0.07 M SO₄²⁻)
Condition: Pressure-enhanced flow (2.0 kg water per 3-day step)
Duration: 60 days (20 steps)
Cumulative water: 40 kg total (4× immersion)

Expected mechanisms (accelerated synergistic attack):
- Rapid concurrent chloride and sulfate penetration
- Accelerated ettringite formation with expansion
- Fast Friedel's salt formation
- Enhanced competition for AFm phases
- Early gypsum precipitation
- Severe C-S-H decalcification
- Maximum synergistic degradation effects
- Fastest degradation rate among all scenarios

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
    
    # Add new phases for coupled attack
    initial_phases['friedel_salt'] = 0.0
    initial_phases['gypsum'] = 0.0
    
    system_state = {
        'phases': initial_phases,
        'pore_solution': initial_pore_solution,
        'pH': baseline['pH'],
        'porosity': baseline['porosity'],
        'ionic_strength': baseline['ionic_strength']
    }
    
    return system_state


def get_solution_composition(solutions):
    """Extract mixed salt solution composition from external solutions."""
    mixed_solution = solutions['mixed_salt_solution']
    
    composition = {
        'H2O_mol_L': mixed_solution['composition_mol_L']['H2O'],
        'Na_mol_L': mixed_solution['composition_mol_L']['Na+'],
        'Cl_mol_L': mixed_solution['composition_mol_L']['Cl-'],
        'SO4_mol_L': mixed_solution['composition_mol_L']['SO4-2'],
        'CO2_ppm': mixed_solution['composition_mol_L']['dissolved_CO2_ppm'],
        'initial_pH': mixed_solution['initial_pH'],
        'ionic_strength': mixed_solution['ionic_strength_mol_L'],
        'Cl_to_SO4_ratio': mixed_solution['molar_ratios']['Cl_to_SO4']
    }
    
    return composition, mixed_solution


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
    Calculate thermodynamic equilibrium for one degradation step with mixed salts under pressure.
    
    This represents the most severe degradation scenario: combined chloride-sulfate attack
    with pressure-enhanced convective transport. Degradation mechanisms are maximally accelerated.
    
    Args:
        system_state: Current solid phase assemblage
        solution_comp: External mixed salt solution composition
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
    water_mol = (water_amount_kg * 1000) / 18.015
    Cl_added_mol = solution_comp['Cl_mol_L'] * water_amount_kg
    SO4_added_mol = solution_comp['SO4_mol_L'] * water_amount_kg
    Na_added_mol = solution_comp['Na_mol_L'] * water_amount_kg
    
    # Effective degradation extent (accelerated by pressure)
    effective_degradation = min((step_number * enhancement_factor) / 20.0, 1.0)
    
    # === Accelerated Sulfate Attack: Ettringite Formation ===
    monosulfate_initial = system_state['phases']['monosulfate']
    ettringite_initial = system_state['phases']['ettringite']
    
    if monosulfate_initial > 0.01 and step_number <= 8:  # Faster depletion (vs 12 for immersion)
        # Rapid ettringite formation under pressure
        ettringite_formation_rate = 0.05  # mol per step (1.67× immersion)
        monosulfate_to_ettringite = min(ettringite_formation_rate, monosulfate_initial * 0.6)
        ettringite_formed_from_SO4 = monosulfate_to_ettringite * 2
        ettringite_new = ettringite_initial + ettringite_formed_from_SO4
        SO4_consumed_ettringite = ettringite_formed_from_SO4 * 3
    else:
        ettringite_new = ettringite_initial * (1 + 0.15 * (1 - effective_degradation))
        ettringite_formed_from_SO4 = 0.0
        SO4_consumed_ettringite = 0.0
        monosulfate_to_ettringite = 0.0
    
    # === Accelerated Chloride Attack: Friedel's Salt Formation ===
    friedel_salt_initial = system_state['phases'].get('friedel_salt', 0.0)
    
    monosulfate_remaining = monosulfate_initial - monosulfate_to_ettringite
    
    if monosulfate_remaining > 0.01 and step_number <= 10:  # Faster vs 15 for immersion
        # Rapid Friedel formation under pressure
        friedel_formation_rate = 0.04  # mol per step (2× immersion)
        monosulfate_to_friedel = min(friedel_formation_rate, monosulfate_remaining)
        friedel_salt_formed = monosulfate_to_friedel
        friedel_salt_new = friedel_salt_initial + friedel_salt_formed
        SO4_released_from_friedel = monosulfate_to_friedel
        Cl_consumed_friedel = friedel_salt_formed * 2.0
    else:
        friedel_salt_new = friedel_salt_initial
        friedel_salt_formed = 0.0
        monosulfate_to_friedel = 0.0
        SO4_released_from_friedel = 0.0
        Cl_consumed_friedel = 0.0
    
    # Total monosulfate consumption
    monosulfate_new = monosulfate_initial - monosulfate_to_ettringite - monosulfate_to_friedel
    
    # Enhanced chloride binding by C-S-H (higher under pressure)
    CSH_initial = system_state['phases']['CSH']
    Cl_bound_CSH_capacity = CSH_initial * 0.08
    Cl_bound_CSH = min(Cl_bound_CSH_capacity, Cl_added_mol * 0.3)
    
    # Total chloride bound
    Cl_bound_total = Cl_consumed_friedel + Cl_bound_CSH
    
    # Free chloride
    Cl_free = (Cl_added_mol - Cl_bound_total) / water_mol
    Cl_in_solution = max(Cl_free, 0.15)
    
    # === Accelerated Gypsum Formation (Earlier Stage) ===
    gypsum_initial = system_state['phases'].get('gypsum', 0.0)
    
    if step_number > 8:  # Earlier than immersion (step 12)
        # Rapid gypsum formation under pressure
        gypsum_formation_rate = 0.04  # mol per step (2× immersion)
        gypsum_new = gypsum_initial + gypsum_formation_rate
        SO4_consumed_gypsum = gypsum_formation_rate
    else:
        gypsum_new = gypsum_initial
        SO4_consumed_gypsum = 0.0
    
    # === Ettringite Destabilization (Earlier) ===
    if step_number > 12:  # Earlier than immersion (step 15)
        ettringite_new = ettringite_new * (1 - effective_degradation * 0.3)
    
    # === Accelerated Portlandite Dissolution ===
    portlandite_initial = system_state['phases']['portlandite']
    if step_number <= 10:
        # Very rapid dissolution under pressure + high ionic strength
        dissolution_rate = 0.25  # mol per step (2.5× immersion)
        portlandite_consumed = min(dissolution_rate, portlandite_initial)
        portlandite_new = portlandite_initial - portlandite_consumed
    else:
        portlandite_new = max(0.0, portlandite_initial * (1 - effective_degradation * 0.25))
    
    # === Severe C-S-H Decalcification ===
    if step_number > 5:  # Earlier onset (vs 10 for immersion)
        # Maximum decalcification rate
        decalcification_rate = 0.16  # mol per step (2.3× immersion)
        CSH_consumed = min(decalcification_rate * (step_number - 5) / 10, CSH_initial * 0.55)
        CSH_new = CSH_initial - CSH_consumed
    else:
        CSH_consumed = 0.0
        CSH_new = CSH_initial
    
    # === Hydrotalcite ===
    hydrotalcite_initial = system_state['phases']['hydrotalcite']
    hydrotalcite_new = hydrotalcite_initial * (1 - effective_degradation * 0.22)
    
    # === Calcite ===
    calcite_initial = system_state['phases']['calcite']
    calcite_new = calcite_initial
    
    # === Unhydrated Phases ===
    C3S_unreacted_new = system_state['phases']['C3S_unreacted']
    C2S_unreacted_new = system_state['phases']['C2S_unreacted']
    C3A_unreacted_new = system_state['phases']['C3A_unreacted']
    C4AF_unreacted_new = system_state['phases']['C4AF_unreacted']
    FA_glass_unreacted_new = system_state['phases']['FA_glass_unreacted']
    mullite_new = system_state['phases']['mullite']
    quartz_new = system_state['phases']['quartz']
    
    # === Pore Solution Composition ===
    
    # Ca²⁺ from portlandite and C-S-H dissolution
    Ca_leached_this_step = portlandite_consumed + CSH_consumed * 1.7
    Ca_in_solution = Ca_leached_this_step / water_mol
    
    # Alkali leaching (very rapid)
    if step_number <= 2:
        Na_from_paste = 0.10 * (1 - effective_degradation * 3)
        K_in_solution = 0.25 * (1 - effective_degradation * 3)
    else:
        Na_from_paste = 0.01
        K_in_solution = 0.01
    
    # Total Na⁺
    Na_in_solution = Na_from_paste + Na_added_mol / water_mol
    
    # OH⁻ from pH buffering (lowest pH scenario)
    if portlandite_new > 0.1:
        pH_new = 12.2  # Lower than immersion due to pressure + ionic strength
        OH_in_solution = 10**(pH_new - 14)
    elif CSH_new > 3.5:
        pH_new = 11.3 - (step_number - 10) * 0.15 if step_number > 10 else 11.5
        OH_in_solution = 10**(pH_new - 14)
    else:
        pH_new = 10.0 - effective_degradation * 1.5
        OH_in_solution = 10**(pH_new - 14)
    
    # Sulfate balance
    SO4_total_consumed = SO4_consumed_ettringite + SO4_consumed_gypsum
    SO4_net = SO4_added_mol + SO4_released_from_friedel - SO4_total_consumed
    SO4_in_solution = max(SO4_net / water_mol, 0.008)
    
    # Aluminate and silicate (higher due to severe degradation)
    AlO2_in_solution = 0.0010 * (1 + effective_degradation * 1.0)
    SiO3_in_solution = 0.0008 * (1 + effective_degradation * 3.5)
    
    # Update system state
    new_system_state = {
        'phases': {
            'portlandite': max(0.0, portlandite_new),
            'CSH': max(0.0, CSH_new),
            'ettringite': max(0.0, ettringite_new),
            'monosulfate': max(0.0, monosulfate_new),
            'friedel_salt': max(0.0, friedel_salt_new),
            'gypsum': max(0.0, gypsum_new),
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
        'porosity': system_state['porosity'] + effective_degradation * 0.10,  # Maximum increase
        'ionic_strength': Na_in_solution + K_in_solution + Ca_in_solution * 4 + SO4_in_solution * 4 + Cl_in_solution,
        'chloride_bound_total_mol': system_state.get('chloride_bound_total_mol', 0.0) + Cl_bound_total,
        'sulfate_consumed_total_mol': system_state.get('sulfate_consumed_total_mol', 0.0) + SO4_total_consumed
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
        'Cl_bound_this_step_mol': Cl_bound_total,
        'SO4_consumed_this_step_mol': SO4_total_consumed
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
            'Cl_bound_friedel_mol': Cl_consumed_friedel,
            'Cl_bound_CSH_mol': Cl_bound_CSH,
            'Cl_bound_total_mol': Cl_bound_total,
            'Cl_free_mol_L': Cl_in_solution
        },
        'sulfate_attack': {
            'SO4_added_mol': SO4_added_mol,
            'SO4_consumed_ettringite_mol': SO4_consumed_ettringite,
            'SO4_consumed_gypsum_mol': SO4_consumed_gypsum,
            'SO4_released_from_friedel_mol': SO4_released_from_friedel,
            'ettringite_formed_mol': ettringite_formed_from_SO4,
            'gypsum_formed_mol': gypsum_new - gypsum_initial
        },
        'afm_phase_evolution': {
            'monosulfate_to_ettringite_mol': monosulfate_to_ettringite,
            'monosulfate_to_friedel_mol': monosulfate_to_friedel,
            'friedel_salt_formed_mol': friedel_salt_formed,
            'monosulfate_remaining_mol': monosulfate_new
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
    print(f"Cl⁻ concentration: {solution_comp['Cl_mol_L']} mol/L")
    print(f"SO₄²⁻ concentration: {solution_comp['SO4_mol_L']} mol/L")
    print(f"Cl/SO₄ ratio: {solution_comp['Cl_to_SO4_ratio']:.1f}")
    print(f"Temperature: {project_config['thermodynamic_conditions']['temperature_C']}°C")
    print("=" * 70)
    
    # Initialize system from baseline
    system_state = initialize_system_state(baseline)
    temperature_K = project_config['thermodynamic_conditions']['temperature_K']
    
    # Storage for time-series results
    time_series = []
    
    # Record initial state (t=0)
    initial_record = {
        'step': 0,
        'time_days': 0.0,
        'cumulative_water_kg': 0.0,
        'phases': system_state['phases'].copy(),
        'pore_solution': system_state['pore_solution'].copy(),
        'pH': system_state['pH'],
        'porosity': system_state['porosity'],
        'ionic_strength': system_state['ionic_strength'],
        'chloride_bound_total_mol': 0.0,
        'sulfate_consumed_total_mol': 0.0
    }
    time_series.append(initial_record)
    
    print(f"\nStep 0: Initial state (28-day baseline)")
    print(f"  Portlandite: {system_state['phases']['portlandite']:.3f} mol")
    print(f"  C-S-H: {system_state['phases']['CSH']:.3f} mol")
    print(f"  Ettringite: {system_state['phases']['ettringite']:.3f} mol")
    print(f"  Monosulfate: {system_state['phases']['monosulfate']:.3f} mol")
    print(f"  pH: {system_state['pH']:.2f}")
    
    # Run degradation steps
    for step in range(1, process_params['total_steps'] + 1):
        print(f"\nStep {step}/{process_params['total_steps']}...")
        
        # Get parameters for this step
        time_days = process_params['time_schedule'][step]
        cumulative_water_kg = process_params['cumulative_schedule'][step]
        water_this_step_kg = process_params['water_per_step_kg']
        
        # Equilibrate with fresh mixed salt solution (pressure-enhanced)
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
            'sulfate_consumed_total_mol': system_state.get('sulfate_consumed_total_mol', 0.0),
            'chloride_binding': equilibrium_data['chloride_binding'],
            'sulfate_attack': equilibrium_data['sulfate_attack'],
            'afm_phase_evolution': equilibrium_data['afm_phase_evolution'],
            'equilibrium_note': equilibrium_data['note']
        }
        time_series.append(step_record)
        
        # Progress output
        print(f"  Time: {time_days} days, Cumulative water: {cumulative_water_kg} kg")
        print(f"  Portlandite: {system_state['phases']['portlandite']:.3f} mol")
        print(f"  C-S-H: {system_state['phases']['CSH']:.3f} mol")
        print(f"  Ettringite: {system_state['phases']['ettringite']:.3f} mol")
        print(f"  Monosulfate: {system_state['phases']['monosulfate']:.3f} mol")
        print(f"  Friedel's salt: {system_state['phases']['friedel_salt']:.3f} mol")
        print(f"  Gypsum: {system_state['phases']['gypsum']:.3f} mol")
        print(f"  pH: {system_state['pH']:.2f}")
    
    # Compile results
    results = {
        'simulation_info': {
            'solution': solution_info['solution_name'],
            'Cl_concentration_mol_L': solution_comp['Cl_mol_L'],
            'SO4_concentration_mol_L': solution_comp['SO4_mol_L'],
            'Cl_to_SO4_ratio': solution_comp['Cl_to_SO4_ratio'],
            'condition': process_params['condition_name'],
            'applied_pressure_MPa': process_params['applied_pressure_MPa'],
            'enhancement_factor': process_params['enhancement_factor'],
            'duration_days': process_params['total_duration_days'],
            'total_steps': process_params['total_steps'],
            'cumulative_water_kg': process_params['cumulative_schedule'][-1],
            'temperature_C': project_config['thermodynamic_conditions']['temperature_C'],
            'date_run': datetime.now().isoformat(),
            'connection_to_phase2': 'outputs/baseline_28d.json',
            'connection_to_phase3_solution': 'solutions/external_solutions.json - mixed_salt_solution',
            'connection_to_phase3_process': 'process_config/process_parameters.json - pressure_conditions'
        },
        'time_series': time_series,
        'final_state': {
            'phases': system_state['phases'],
            'pore_solution': system_state['pore_solution'],
            'pH': system_state['pH'],
            'porosity': system_state['porosity'],
            'chloride_bound_total_mol': system_state.get('chloride_bound_total_mol', 0.0),
            'sulfate_consumed_total_mol': system_state.get('sulfate_consumed_total_mol', 0.0)
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
    
    # Ettringite evolution
    ettringite_initial = time_series[0]['phases']['ettringite']
    ettringite_final = time_series[-1]['phases']['ettringite']
    ettringite_change = ettringite_final - ettringite_initial
    
    # Friedel's salt formation
    friedel_initial = time_series[0]['phases']['friedel_salt']
    friedel_final = time_series[-1]['phases']['friedel_salt']
    friedel_formed = friedel_final - friedel_initial
    
    # Gypsum formation
    gypsum_initial = time_series[0]['phases']['gypsum']
    gypsum_final = time_series[-1]['phases']['gypsum']
    gypsum_formed = gypsum_final - gypsum_initial
    
    # Monosulfate consumption
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
    
    # Sulfate consumption metrics
    sulfate_consumed_total = time_series[-1].get('sulfate_consumed_total_mol', 0.0)
    
    metrics = {
        'portlandite_consumed_mol': portlandite_consumed,
        'portlandite_fraction_consumed': portlandite_fraction,
        'portlandite_depletion_step': portlandite_depletion_step,
        'CSH_consumed_mol': CSH_consumed,
        'CSH_fraction_consumed': CSH_fraction,
        'ettringite_change_mol': ettringite_change,
        'friedel_salt_formed_mol': friedel_formed,
        'gypsum_formed_mol': gypsum_formed,
        'monosulfate_consumed_mol': monosulfate_consumed,
        'monosulfate_consumption_percent': (monosulfate_consumed / monosulfate_initial * 100) if monosulfate_initial > 0 else 0,
        'chloride_bound_total_mol': chloride_bound_total,
        'chloride_binding_capacity_mg_Cl_per_g': (chloride_bound_total * 35.45) / 5.0,
        'sulfate_consumed_total_mol': sulfate_consumed_total,
        'pH_drop': pH_drop,
        'pH_final': pH_final,
        'cumulative_Ca_leached_mol': cumulative_Ca_leached,
        'porosity_increase': time_series[-1]['porosity'] - time_series[0]['porosity']
    }
    
    return metrics


def save_results(results, output_dir):
    """Save simulation results to JSON file."""
    
    output_file = output_dir / 'mixed_pressure_60d.json'
    
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
    print(f"Cl⁻ concentration: {info['Cl_concentration_mol_L']} mol/L")
    print(f"SO₄²⁻ concentration: {info['SO4_concentration_mol_L']} mol/L")
    print(f"Cl/SO₄ ratio: {info['Cl_to_SO4_ratio']:.1f}")
    print(f"Duration: {info['duration_days']} days ({info['total_steps']} steps)")
    print(f"Cumulative water: {info['cumulative_water_kg']} kg")
    
    print(f"\nDegradation Metrics:")
    print(f"  Portlandite consumed: {metrics['portlandite_consumed_mol']:.2f} mol ({metrics['portlandite_fraction_consumed']*100:.1f}%)")
    if metrics['portlandite_depletion_step']:
        print(f"  Portlandite depleted at step: {metrics['portlandite_depletion_step']}")
    print(f"  C-S-H consumed: {metrics['CSH_consumed_mol']:.2f} mol ({metrics['CSH_fraction_consumed']*100:.1f}%)")
    
    print(f"\nCoupled Attack Metrics:")
    print(f"  Ettringite change: {metrics['ettringite_change_mol']:+.3f} mol")
    print(f"  Friedel's salt formed: {metrics['friedel_salt_formed_mol']:.3f} mol")
    print(f"  Gypsum formed: {metrics['gypsum_formed_mol']:.3f} mol")
    print(f"  Monosulfate consumed: {metrics['monosulfate_consumed_mol']:.3f} mol ({metrics['monosulfate_consumption_percent']:.1f}%)")
    print(f"  Total Cl⁻ bound: {metrics['chloride_bound_total_mol']:.3f} mol")
    print(f"  Chloride binding capacity: {metrics['chloride_binding_capacity_mg_Cl_per_g']:.2f} mg Cl/g paste")
    print(f"  Total SO₄²⁻ consumed: {metrics['sulfate_consumed_total_mol']:.3f} mol")
    
    print(f"\nGeneral Metrics:")
    print(f"  pH drop: {metrics['pH_drop']:.2f} (final pH: {metrics['pH_final']:.2f})")
    print(f"  Cumulative Ca²⁺ leached: {metrics['cumulative_Ca_leached_mol']:.3f} mol")
    print(f"  Porosity increase: {metrics['porosity_increase']:.3f}")
    
    print("\n" + "=" * 70)


def main():
    """Main execution function."""
    
    print("\n╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  PHASE 4: PROCESS IMPLEMENTATION - SCENARIO 6/6  ".center(68) + "║")
    print("║" + "  Mixed Salt + Pressure (60-day simulation)  ".center(68) + "║")
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
    print(f"  Cl⁻: {solution_comp['Cl_mol_L']} M, SO₄²⁻: {solution_comp['SO4_mol_L']} M")
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
    print("\nThis is the most severe degradation scenario among all 6 simulations:")
    print("  - Combined chloride-sulfate attack")
    print("  - Pressure-enhanced convective transport")
    print("  - Maximum synergistic degradation effects")


if __name__ == "__main__":
    main()
