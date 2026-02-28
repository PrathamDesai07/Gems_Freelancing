#!/usr/bin/env python3
"""
Phase 5: Phase 4 Output Validation

This script validates Phase 4 degradation simulation outputs for physical
consistency, mass balance, and realistic degradation behavior.

NO MOCK DATA - Validates against real experimental constraints
NO RANDOM GENERATION - Deterministic validation checks only

Connects to:
- Phase 4: All 6 simulation output files (*_60d.json)
- Phase 2: baseline_28d.json (initial state reference)
- Phase 5: Validation criteria from experimental data

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
    Load Phase 4 simulation output file.
    
    Args:
        filepath: Path to simulation output JSON
        
    Returns:
        Simulation data dictionary
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Simulation output not found: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return data


def validate_mass_balance(sim_data: Dict) -> Dict:
    """
    Validate mass balance throughout simulation.
    
    Mass should be conserved: initial solid + added solution = final solid + removed solution
    
    Args:
        sim_data: Simulation data
        
    Returns:
        Validation results
    """
    results = {
        'check': 'mass_balance',
        'status': 'unknown',
        'errors': [],
        'warnings': []
    }
    
    # Check if time series exists
    if 'time_series' not in sim_data:
        results['status'] = 'error'
        results['errors'].append("No time_series data found")
        return results
    
    time_series = sim_data['time_series']
    
    # Check each step for mass balance
    mass_errors = []
    for i, step in enumerate(time_series):
        step_num = step.get('step', i)
        
        # Get total phase mass (if available)
        if 'phase_assemblage' in step:
            total_mass = 0
            for phase, data in step['phase_assemblage'].items():
                if isinstance(data, dict) and 'mass_g' in data:
                    total_mass += data['mass_g']
            
            # Initial mass should be ~100g (5g specimen scaled to 100g basis)
            if step_num == 0:
                initial_mass = total_mass
                if abs(total_mass - 100) > 5:
                    results['warnings'].append(
                        f"Step {step_num}: Initial mass {total_mass:.2f}g deviates from 100g basis"
                    )
            else:
                # Check if mass changes are reasonable
                # Degradation should decrease solid mass (leaching)
                if total_mass > initial_mass + 1:
                    mass_errors.append(
                        f"Step {step_num}: Mass increased ({total_mass:.2f}g > {initial_mass:.2f}g)"
                    )
    
    if mass_errors:
        results['status'] = 'warning'
        results['warnings'].extend(mass_errors[:5])  # Limit to first 5
    else:
        results['status'] = 'pass'
    
    return results


def validate_pH_progression(sim_data: Dict, scenario_type: str) -> Dict:
    """
    Validate pH evolution is physically realistic.
    
    Expected:
    - Initial pH ~13.7 (high alkali)
    - Stage 1: Slight drop to ~13.5 (alkali leaching)
    - Stage 2: Plateau at ~12.5 (portlandite buffering)
    - Stage 3: Drop to 11-12 (C-S-H decalcification)
    - pH should never increase during degradation
    
    Args:
        sim_data: Simulation data
        scenario_type: Type of scenario (PW, NaCl, mixed)
        
    Returns:
        Validation results
    """
    results = {
        'check': 'pH_progression',
        'status': 'unknown',
        'errors': [],
        'warnings': []
    }
    
    if 'time_series' not in sim_data:
        results['status'] = 'error'
        results['errors'].append("No time_series data")
        return results
    
    time_series = sim_data['time_series']
    
    # Extract pH values
    pH_values = []
    for step in time_series:
        if 'pore_solution' in step and 'pH' in step['pore_solution']:
            pH_values.append(step['pore_solution']['pH'])
    
    if not pH_values:
        results['status'] = 'warning'
        results['warnings'].append("No pH data available")
        return results
    
    # Check initial pH
    initial_pH = pH_values[0]
    if initial_pH < 13.0 or initial_pH > 14.0:
        results['warnings'].append(f"Initial pH {initial_pH:.2f} outside typical range [13.0-14.0]")
    
    # Check pH never increases
    pH_increases = []
    for i in range(1, len(pH_values)):
        if pH_values[i] > pH_values[i-1] + 0.1:  # Allow small numerical fluctuations
            pH_increases.append(f"Step {i}: pH increased from {pH_values[i-1]:.2f} to {pH_values[i]:.2f}")
    
    if pH_increases:
        results['status'] = 'error'
        results['errors'].append(f"pH increased in {len(pH_increases)} steps (should only decrease)")
        results['errors'].extend(pH_increases[:3])
    else:
        results['status'] = 'pass'
    
    # Check final pH is reasonable
    final_pH = pH_values[-1]
    if scenario_type == 'PW':
        if final_pH < 11.0:
            results['warnings'].append(f"Final pH {final_pH:.2f} very low for pure water (expected 11-12.5)")
    
    return results


def validate_portlandite_depletion(sim_data: Dict) -> Dict:
    """
    Validate portlandite dissolution follows expected pattern.
    
    Expected:
    - Monotonic decrease
    - Complete depletion marks end of Stage 2
    - Depletion rate depends on water contact
    
    Args:
        sim_data: Simulation data
        
    Returns:
        Validation results
    """
    results = {
        'check': 'portlandite_depletion',
        'status': 'unknown',
        'errors': [],
        'warnings': []
    }
    
    if 'time_series' not in sim_data:
        results['status'] = 'error'
        results['errors'].append("No time_series data")
        return results
    
    time_series = sim_data['time_series']
    
    # Extract portlandite amounts
    CH_values = []
    for step in time_series:
        if 'phase_assemblage' in step:
            phases = step['phase_assemblage']
            # Try different possible names
            CH_amount = 0
            for phase_name in ['portlandite', 'Ca(OH)2', 'CH']:
                if phase_name in phases:
                    phase_data = phases[phase_name]
                    if isinstance(phase_data, dict):
                        CH_amount = phase_data.get('amount_mol', 0)
                    break
            CH_values.append(CH_amount)
    
    if not CH_values or all(v == 0 for v in CH_values):
        results['status'] = 'warning'
        results['warnings'].append("No portlandite data found")
        return results
    
    # Check monotonic decrease
    for i in range(1, len(CH_values)):
        if CH_values[i] > CH_values[i-1] + 1e-6:  # Small tolerance
            results['errors'].append(
                f"Step {i}: Portlandite increased from {CH_values[i-1]:.4f} to {CH_values[i]:.4f} mol"
            )
    
    if results['errors']:
        results['status'] = 'error'
    else:
        results['status'] = 'pass'
        
        # Additional check: find depletion step
        depletion_step = None
        for i, val in enumerate(CH_values):
            if val < 0.01:  # Effectively zero
                depletion_step = i
                break
        
        if depletion_step:
            results['info'] = f"Portlandite depleted at step {depletion_step} ({depletion_step*3} days)"
    
    return results


def validate_CSH_evolution(sim_data: Dict, scenario_type: str) -> Dict:
    """
    Validate C-S-H gel evolution.
    
    Expected:
    - Should decrease during degradation (decalcification)
    - Ca/Si ratio should decrease
    - More severe in aggressive scenarios
    
    Args:
        sim_data: Simulation data
        scenario_type: Scenario type
        
    Returns:
        Validation results
    """
    results = {
        'check': 'CSH_evolution',
        'status': 'unknown',
        'errors': [],
        'warnings': []
    }
    
    if 'time_series' not in sim_data:
        results['status'] = 'error'
        results['errors'].append("No time_series data")
        return results
    
    time_series = sim_data['time_series']
    
    # Extract C-S-H amounts
    CSH_values = []
    for step in time_series:
        if 'phase_assemblage' in step:
            phases = step['phase_assemblage']
            for phase_name in ['CSH_gel', 'C-S-H', 'CSH']:
                if phase_name in phases:
                    phase_data = phases[phase_name]
                    if isinstance(phase_data, dict):
                        CSH_values.append(phase_data.get('amount_mol', 0))
                    break
    
    if not CSH_values:
        results['status'] = 'warning'
        results['warnings'].append("No C-S-H data found")
        return results
    
    # Check if C-S-H decreases overall
    initial_CSH = CSH_values[0]
    final_CSH = CSH_values[-1]
    
    if final_CSH > initial_CSH:
        results['errors'].append(
            f"C-S-H increased during degradation ({initial_CSH:.2f} → {final_CSH:.2f} mol)"
        )
        results['status'] = 'error'
    else:
        CSH_loss_percent = (initial_CSH - final_CSH) / initial_CSH * 100
        results['status'] = 'pass'
        results['info'] = f"C-S-H loss: {CSH_loss_percent:.1f}%"
        
        # Check if loss is reasonable for scenario
        if scenario_type == 'mixed' and CSH_loss_percent < 20:
            results['warnings'].append(
                f"C-S-H loss {CSH_loss_percent:.1f}% seems low for aggressive mixed salt scenario"
            )
    
    return results


def validate_chloride_binding(sim_data: Dict) -> Dict:
    """
    Validate chloride binding behavior for NaCl scenarios.
    
    Expected:
    - Friedel's salt formation
    - Monosulfate conversion
    - C-S-H chloride adsorption
    - Total binding capacity realistic
    
    Args:
        sim_data: Simulation data
        
    Returns:
        Validation results
    """
    results = {
        'check': 'chloride_binding',
        'status': 'unknown',
        'errors': [],
        'warnings': []
    }
    
    # Check if this is a chloride scenario
    sim_info = sim_data.get('simulation_info', {})
    solution = sim_info.get('external_solution', '')
    
    if 'NaCl' not in solution and 'mixed' not in solution.lower():
        results['status'] = 'not_applicable'
        results['info'] = "Not a chloride scenario"
        return results
    
    if 'time_series' not in sim_data:
        results['status'] = 'error'
        results['errors'].append("No time_series data")
        return results
    
    time_series = sim_data['time_series']
    
    # Extract Friedel's salt
    Friedel_values = []
    for step in time_series:
        if 'phase_assemblage' in step:
            phases = step['phase_assemblage']
            for phase_name in ['friedel_salt', 'Friedel_salt', 'Friedels_salt']:
                if phase_name in phases:
                    phase_data = phases[phase_name]
                    if isinstance(phase_data, dict):
                        Friedel_values.append(phase_data.get('amount_mol', 0))
                    break
    
    if not Friedel_values:
        results['status'] = 'warning'
        results['warnings'].append("No Friedel's salt formation detected in chloride scenario")
        return results
    
    # Check Friedel's salt increases
    initial_Friedel = Friedel_values[0]
    final_Friedel = Friedel_values[-1]
    
    if final_Friedel <= initial_Friedel:
        results['errors'].append(
            f"Friedel's salt did not increase during chloride exposure ({initial_Friedel:.4f} → {final_Friedel:.4f} mol)"
        )
        results['status'] = 'error'
    else:
        Friedel_formed = final_Friedel - initial_Friedel
        results['status'] = 'pass'
        results['info'] = f"Friedel's salt formed: {Friedel_formed:.4f} mol"
        
        # Check if formation is reasonable (should be <0.5 mol for 5g specimen)
        if Friedel_formed > 0.5:
            results['warnings'].append(
                f"Friedel's salt formation {Friedel_formed:.4f} mol seems high"
            )
    
    return results


def validate_sulfate_attack(sim_data: Dict) -> Dict:
    """
    Validate sulfate attack behavior for mixed salt scenarios.
    
    Expected:
    - Ettringite formation (early)
    - Possible gypsum formation (late)
    - C-S-H decalcification
    
    Args:
        sim_data: Simulation data
        
    Returns:
        Validation results
    """
    results = {
        'check': 'sulfate_attack',
        'status': 'unknown',
        'errors': [],
        'warnings': []
    }
    
    # Check if this is a sulfate scenario
    sim_info = sim_data.get('simulation_info', {})
    solution = sim_info.get('external_solution', '')
    
    if 'mixed' not in solution.lower() and 'SO4' not in solution:
        results['status'] = 'not_applicable'
        results['info'] = "Not a sulfate scenario"
        return results
    
    if 'time_series' not in sim_data:
        results['status'] = 'error'
        results['errors'].append("No time_series data")
        return results
    
    time_series = sim_data['time_series']
    
    # Extract ettringite
    ettringite_values = []
    for step in time_series:
        if 'phase_assemblage' in step:
            phases = step['phase_assemblage']
            for phase_name in ['ettringite', 'AFt']:
                if phase_name in phases:
                    phase_data = phases[phase_name]
                    if isinstance(phase_data, dict):
                        ettringite_values.append(phase_data.get('amount_mol', 0))
                    break
    
    if not ettringite_values:
        results['status'] = 'warning'
        results['warnings'].append("No ettringite data in sulfate scenario")
        return results
    
    initial_ett = ettringite_values[0]
    max_ett = max(ettringite_values)
    final_ett = ettringite_values[-1]
    
    # Ettringite should increase initially
    if max_ett > initial_ett:
        results['status'] = 'pass'
        results['info'] = f"Ettringite formation detected: {initial_ett:.4f} → {max_ett:.4f} mol"
    else:
        results['status'] = 'warning'
        results['warnings'].append("No ettringite formation in sulfate scenario")
    
    # Check if ettringite decomposes later
    if final_ett < max_ett * 0.8:
        results['info'] += f"; Late-stage decomposition observed"
    
    return results


def validate_simulation_outputs(outputs_dir: str, scenarios: List[str]) -> Dict:
    """
    Validate all Phase 4 simulation outputs.
    
    Args:
        outputs_dir: Directory containing simulation outputs
        scenarios: List of scenario names
        
    Returns:
        Complete validation results
    """
    print(f"\n{'='*80}")
    print("VALIDATING PHASE 4 SIMULATION OUTPUTS")
    print(f"{'='*80}")
    
    validation_results = {}
    
    for scenario in scenarios:
        print(f"\n--- Validating: {scenario} ---")
        
        filepath = os.path.join(outputs_dir, f"{scenario}_60d.json")
        
        if not os.path.exists(filepath):
            print(f"⚠ File not found: {filepath}")
            validation_results[scenario] = {
                'status': 'missing',
                'error': 'Output file not found'
            }
            continue
        
        try:
            sim_data = load_simulation_output(filepath)
            
            # Determine scenario type
            scenario_lower = scenario.lower()
            if 'mixed' in scenario_lower:
                scenario_type = 'mixed'
            elif 'nacl' in scenario_lower:
                scenario_type = 'NaCl'
            else:
                scenario_type = 'PW'
            
            # Run validation checks
            checks = {
                'mass_balance': validate_mass_balance(sim_data),
                'pH_progression': validate_pH_progression(sim_data, scenario_type),
                'portlandite_depletion': validate_portlandite_depletion(sim_data),
                'CSH_evolution': validate_CSH_evolution(sim_data, scenario_type),
                'chloride_binding': validate_chloride_binding(sim_data),
                'sulfate_attack': validate_sulfate_attack(sim_data)
            }
            
            # Count passes/failures
            n_pass = sum(1 for c in checks.values() if c['status'] == 'pass')
            n_warning = sum(1 for c in checks.values() if c['status'] == 'warning')
            n_error = sum(1 for c in checks.values() if c['status'] == 'error')
            n_na = sum(1 for c in checks.values() if c['status'] == 'not_applicable')
            
            overall_status = 'PASS' if n_error == 0 else ('WARNING' if n_warning > 0 else 'FAIL')
            
            validation_results[scenario] = {
                'status': overall_status,
                'checks': checks,
                'summary': {
                    'passed': n_pass,
                    'warnings': n_warning,
                    'errors': n_error,
                    'not_applicable': n_na
                }
            }
            
            print(f"✓ Validation complete: {overall_status}")
            print(f"  Passed: {n_pass}, Warnings: {n_warning}, Errors: {n_error}")
            
        except Exception as e:
            print(f"✗ Error validating {scenario}: {e}")
            validation_results[scenario] = {
                'status': 'error',
                'error': str(e)
            }
    
    return validation_results


def print_validation_summary(results: Dict):
    """
    Print formatted validation summary.
    
    Args:
        results: Validation results
    """
    print(f"\n{'='*80}")
    print("PHASE 4 OUTPUT VALIDATION SUMMARY")
    print(f"{'='*80}")
    print(f"{'Scenario':<30} {'Status':<15} {'Passed':<10} {'Warnings':<10} {'Errors':<10}")
    print(f"{'-'*80}")
    
    for scenario, data in results.items():
        status = data.get('status', 'unknown')
        summary = data.get('summary', {})
        passed = summary.get('passed', 0)
        warnings = summary.get('warnings', 0)
        errors = summary.get('errors', 0)
        
        status_symbol = '✓' if status == 'PASS' else ('⚠' if status == 'WARNING' else '✗')
        
        print(f"{scenario:<30} {status_symbol} {status:<13} {passed:<10} {warnings:<10} {errors:<10}")


def save_validation_report(output_dir: str, results: Dict):
    """
    Save validation report to JSON.
    
    Args:
        output_dir: Output directory
        results: Validation results
    """
    os.makedirs(output_dir, exist_ok=True)
    
    report_data = {
        'validation_info': {
            'description': 'Phase 5: Phase 4 simulation output validation',
            'validation_date': '2026-02-28',
            'total_scenarios_validated': len(results)
        },
        'validation_results': results,
        'validation_criteria': {
            'mass_balance': 'Mass conservation throughout simulation',
            'pH_progression': 'Physically realistic pH decrease',
            'portlandite_depletion': 'Monotonic portlandite dissolution',
            'CSH_evolution': 'C-S-H decalcification during degradation',
            'chloride_binding': 'Friedel salt formation in chloride scenarios',
            'sulfate_attack': 'Ettringite formation in sulfate scenarios'
        }
    }
    
    output_file = os.path.join(output_dir, 'phase4_validation_report.json')
    
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n✓ Validation report saved to: {output_file}")


def main():
    """
    Main validation workflow.
    """
    print(f"\n{'#'*80}")
    print("PHASE 5: PHASE 4 OUTPUT VALIDATION")
    print("Physical Consistency and Degradation Behavior Checks")
    print(f"{'#'*80}")
    
    # Define paths
    project_root = Path(__file__).parent.parent
    outputs_dir = project_root / 'outputs'
    validation_dir = project_root / 'validation' / 'phase4_validation'
    
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
        # Validate all outputs
        results = validate_simulation_outputs(str(outputs_dir), scenarios)
        
        # Print summary
        print_validation_summary(results)
        
        # Save report
        save_validation_report(str(validation_dir), results)
        
        print(f"\n{'='*80}")
        print("VALIDATION COMPLETE")
        print(f"{'='*80}")
        
        # Check overall status
        all_pass = all(r.get('status') in ['PASS', 'missing'] for r in results.values())
        
        if all_pass:
            print("✓ All available simulation outputs passed validation")
            return 0
        else:
            print("⚠ Some simulation outputs have warnings or errors")
            print("  Review validation report for details")
            return 1
    
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
