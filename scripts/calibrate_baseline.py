#!/usr/bin/env python3
"""
Phase 5: Calibration - Baseline Model vs Experimental Data

This script compares the Phase 2 baseline model (baseline_28d.json) with 
experimental XRD/TGA measurements to validate the thermodynamic model and 
identify any needed calibration adjustments.

NO MOCK DATA - Uses real experimental measurements from validation/experimental_data_28d.json
NO RANDOM GENERATION - All calculations deterministic

Connects to:
- Phase 2: baseline_28d.json (model predictions)
- Phase 5: experimental_data_28d.json (experimental measurements)

Author: GEMS Modeling Team
Date: February 2026
"""

import json
import os
import sys
from pathlib import Path
import numpy as np
from typing import Dict, List, Tuple, Any


def load_experimental_data(filepath: str) -> Dict:
    """
    Load experimental XRD/TGA data from Phase 5 validation file.
    
    Args:
        filepath: Path to experimental_data_28d.json
        
    Returns:
        Dictionary containing experimental measurements
    """
    print(f"\n{'='*80}")
    print("LOADING EXPERIMENTAL DATA")
    print(f"{'='*80}")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Experimental data file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    print(f"✓ Loaded experimental data from: {filepath}")
    print(f"  Specimen: {data['experimental_info']['specimen_id']}")
    print(f"  Mix design: w/b={data['experimental_info']['mix_design']['water_binder_ratio']}, "
          f"{data['experimental_info']['mix_design']['fly_ash_replacement']}% FA")
    print(f"  Curing: {data['experimental_info']['curing_conditions']['duration_days']} days "
          f"at {data['experimental_info']['curing_conditions']['temperature_C']}°C")
    print(f"  Measurement methods: XRD (Rietveld), TGA")
    
    return data


def load_baseline_model(filepath: str) -> Dict:
    """
    Load Phase 2 baseline model predictions.
    
    Args:
        filepath: Path to baseline_28d.json
        
    Returns:
        Dictionary containing model predictions
    """
    print(f"\n{'='*80}")
    print("LOADING BASELINE MODEL PREDICTIONS")
    print(f"{'='*80}")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Baseline model file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    print(f"✓ Loaded baseline model from: {filepath}")
    print(f"  Model: {data.get('model_info', {}).get('description', 'N/A')}")
    print(f"  Temperature: {data.get('conditions', {}).get('temperature_C', 'N/A')}°C")
    print(f"  Hydration age: {data.get('conditions', {}).get('age_days', 'N/A')} days")
    
    return data


def extract_experimental_phases(exp_data: Dict) -> Dict[str, Dict[str, float]]:
    """
    Extract phase assemblage from experimental data with uncertainties.
    
    Args:
        exp_data: Experimental data dictionary
        
    Returns:
        Dictionary of phase names to {content, uncertainty}
    """
    phases = {}
    
    # Get derived phase assemblage (combined XRD+TGA)
    derived = exp_data['derived_phase_assemblage']['phases']
    
    for phase_name, phase_data in derived.items():
        phases[phase_name] = {
            'content_wt_percent': phase_data['content_wt_percent'],
            'uncertainty': phase_data.get('uncertainty', 0.5),
            'source': phase_data.get('source', 'XRD+TGA'),
            'notes': phase_data.get('notes', '')
        }
    
    return phases


def extract_model_phases(model_data: Dict) -> Dict[str, float]:
    """
    Extract phase assemblage from baseline model predictions.
    
    Args:
        model_data: Baseline model dictionary
        
    Returns:
        Dictionary of phase names to content (wt%)
    """
    phases = {}
    
    # Extract from phase_assemblage section
    if 'phase_assemblage' in model_data:
        for phase_name, phase_data in model_data['phase_assemblage'].items():
            if isinstance(phase_data, dict) and 'amount_mol' in phase_data:
                # Convert mol to wt% if molar mass available
                mol = phase_data['amount_mol']
                molar_mass = phase_data.get('molar_mass_g_mol', 0)
                if molar_mass > 0:
                    mass_g = mol * molar_mass
                    # Assume 100g paste basis
                    phases[phase_name] = mass_g
    
    # Normalize to wt%
    total = sum(phases.values())
    if total > 0:
        phases = {k: (v/total)*100 for k, v in phases.items()}
    
    return phases


def map_phase_names(exp_phases: Dict, model_phases: Dict) -> Dict[str, Tuple[str, str]]:
    """
    Map experimental phase names to model phase names.
    
    Some phases may have different naming conventions between XRD and
    thermodynamic modeling.
    
    Args:
        exp_phases: Experimental phase dict
        model_phases: Model phase dict
        
    Returns:
        Dictionary mapping: common_name -> (exp_name, model_name)
    """
    # Define phase name mappings
    phase_map = {
        'portlandite': ('portlandite', 'Ca(OH)2'),
        'CSH_gel': ('CSH_gel', 'C-S-H'),
        'ettringite': ('ettringite', 'ettringite'),
        'monosulfate': ('monosulfate', 'monosulfoaluminate'),
        'hydrotalcite': ('hydrotalcite', 'hydrotalcite'),
        'C3S_unreacted': ('C3S_unreacted', 'C3S'),
        'C2S_unreacted': ('C2S_unreacted', 'C2S'),
        'C4AF_unreacted': ('C4AF_unreacted', 'C4AF'),
        'calcite': ('calcite', 'calcite'),
        'FA_glass': ('FA_glass_unreacted', 'FA_glass'),
        'mullite': ('mullite', 'mullite'),
        'quartz': ('quartz', 'quartz')
    }
    
    return phase_map


def calculate_phase_errors(exp_phases: Dict, model_phases: Dict, 
                          phase_map: Dict) -> Dict[str, Dict]:
    """
    Calculate errors between experimental and model predictions.
    
    Args:
        exp_phases: Experimental phase contents
        model_phases: Model phase contents
        phase_map: Phase name mapping
        
    Returns:
        Dictionary with error metrics for each phase
    """
    errors = {}
    
    for common_name, (exp_name, model_name) in phase_map.items():
        # Get experimental value
        exp_val = 0.0
        exp_unc = 0.0
        if exp_name in exp_phases:
            exp_val = exp_phases[exp_name]['content_wt_percent']
            exp_unc = exp_phases[exp_name]['uncertainty']
        
        # Get model value - try multiple possible names
        model_val = 0.0
        model_found = False
        for possible_name in [model_name, exp_name, common_name]:
            if possible_name in model_phases:
                model_val = model_phases[possible_name]
                model_found = True
                break
        
        # Calculate errors
        absolute_error = model_val - exp_val
        relative_error = (absolute_error / exp_val * 100) if exp_val > 0 else 0
        
        # Check if within uncertainty
        within_uncertainty = abs(absolute_error) <= exp_unc if exp_unc > 0 else False
        
        errors[common_name] = {
            'experimental_wt_percent': exp_val,
            'experimental_uncertainty': exp_unc,
            'model_wt_percent': model_val,
            'model_found': model_found,
            'absolute_error': absolute_error,
            'relative_error_percent': relative_error,
            'within_uncertainty': within_uncertainty,
            'significance': 'critical' if common_name in ['portlandite', 'CSH_gel', 'ettringite'] else 'secondary'
        }
    
    return errors


def calculate_overall_metrics(errors: Dict) -> Dict:
    """
    Calculate overall calibration metrics.
    
    Args:
        errors: Phase-by-phase error dictionary
        
    Returns:
        Dictionary of overall metrics
    """
    # Get absolute and relative errors for all phases
    abs_errors = [e['absolute_error'] for e in errors.values() if e['model_found']]
    rel_errors = [e['relative_error_percent'] for e in errors.values() 
                  if e['model_found'] and e['experimental_wt_percent'] > 0.5]
    
    # Calculate statistics
    mae = np.mean(np.abs(abs_errors)) if abs_errors else 0
    rmse = np.sqrt(np.mean(np.square(abs_errors))) if abs_errors else 0
    mean_rel_error = np.mean(np.abs(rel_errors)) if rel_errors else 0
    
    # Count phases within uncertainty
    total_phases = len([e for e in errors.values() if e['model_found']])
    within_unc = len([e for e in errors.values() if e['within_uncertainty']])
    
    return {
        'mean_absolute_error_wt_percent': mae,
        'root_mean_square_error_wt_percent': rmse,
        'mean_relative_error_percent': mean_rel_error,
        'total_phases_compared': total_phases,
        'phases_within_uncertainty': within_unc,
        'calibration_quality_percent': (within_unc / total_phases * 100) if total_phases > 0 else 0
    }


def compare_pore_solution(exp_data: Dict, model_data: Dict) -> Dict:
    """
    Compare pore solution chemistry predictions.
    
    Args:
        exp_data: Experimental data
        model_data: Model predictions
        
    Returns:
        Comparison dictionary
    """
    comparison = {}
    
    # Get experimental pore solution
    exp_ps = exp_data.get('pore_solution_chemistry', {})
    exp_conc = exp_ps.get('measured_concentrations_mmol_L', {})
    exp_pH = exp_ps.get('pH_measured', 0)
    
    # Get model pore solution (if available)
    model_ps = model_data.get('pore_solution', {})
    model_conc = model_ps.get('concentrations_mmol_L', {})
    model_pH = model_ps.get('pH', 0)
    
    # Compare pH
    comparison['pH'] = {
        'experimental': exp_pH,
        'model': model_pH,
        'error': model_pH - exp_pH,
        'tolerance': 0.2
    }
    
    # Compare major ions
    for ion in ['Na', 'K', 'Ca', 'SO4', 'OH']:
        exp_val = exp_conc.get(ion, 0)
        model_val = model_conc.get(ion, 0)
        
        comparison[ion] = {
            'experimental_mmol_L': exp_val,
            'model_mmol_L': model_val,
            'absolute_error': model_val - exp_val,
            'relative_error_percent': ((model_val - exp_val) / exp_val * 100) if exp_val > 0 else 0
        }
    
    return comparison


def generate_calibration_recommendations(errors: Dict, metrics: Dict) -> List[str]:
    """
    Generate specific calibration recommendations based on errors.
    
    Args:
        errors: Phase error dictionary
        metrics: Overall metrics
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # Check overall calibration quality
    if metrics['calibration_quality_percent'] >= 80:
        recommendations.append("✓ GOOD: Overall calibration quality >80% - model well-calibrated")
    elif metrics['calibration_quality_percent'] >= 60:
        recommendations.append("⚠ FAIR: Calibration quality 60-80% - minor adjustments recommended")
    else:
        recommendations.append("✗ POOR: Calibration quality <60% - significant adjustments needed")
    
    # Check critical phases
    for phase in ['portlandite', 'CSH_gel', 'ettringite']:
        if phase in errors:
            err = errors[phase]
            if not err['within_uncertainty']:
                rel_err = err['relative_error_percent']
                if abs(rel_err) > 20:
                    recommendations.append(
                        f"⚠ {phase.upper()}: {rel_err:+.1f}% error - "
                        f"adjust {'hydration degree' if 'unreacted' in phase else 'thermodynamic parameters'}"
                    )
    
    # Check mass balance
    total_exp = sum(e['experimental_wt_percent'] for e in errors.values())
    total_model = sum(e['model_wt_percent'] for e in errors.values() if e['model_found'])
    
    if abs(total_exp - 100) > 2:
        recommendations.append(f"⚠ Experimental mass balance: {total_exp:.1f}% (should be ~100%)")
    
    if abs(total_model - 100) > 2:
        recommendations.append(f"⚠ Model mass balance: {total_model:.1f}% - check normalization")
    
    # Check if key phases are missing
    missing_phases = [name for name, err in errors.items() 
                     if err['significance'] == 'critical' and not err['model_found']]
    if missing_phases:
        recommendations.append(f"✗ CRITICAL: Missing phases in model: {', '.join(missing_phases)}")
    
    return recommendations


def print_comparison_table(errors: Dict):
    """
    Print formatted comparison table.
    
    Args:
        errors: Phase error dictionary
    """
    print(f"\n{'='*80}")
    print("PHASE ASSEMBLAGE COMPARISON")
    print(f"{'='*80}")
    print(f"{'Phase':<20} {'Exp (wt%)':<12} {'Model (wt%)':<12} {'Error':<12} {'Status':<10}")
    print(f"{'-'*80}")
    
    # Sort by significance and experimental content
    sorted_phases = sorted(errors.items(), 
                          key=lambda x: (x[1]['significance'] != 'critical', 
                                       -x[1]['experimental_wt_percent']))
    
    for phase_name, err in sorted_phases:
        exp_val = err['experimental_wt_percent']
        model_val = err['model_wt_percent']
        abs_err = err['absolute_error']
        within = '✓' if err['within_uncertainty'] else '✗'
        
        # Color coding based on magnitude
        if exp_val > 10 or err['significance'] == 'critical':
            print(f"{phase_name:<20} {exp_val:>10.2f}  {model_val:>10.2f}  "
                  f"{abs_err:>+10.2f}  {within:>8}")
        elif exp_val > 1:
            print(f"{phase_name:<20} {exp_val:>10.2f}  {model_val:>10.2f}  "
                  f"{abs_err:>+10.2f}  {within:>8}")
        else:
            print(f"{phase_name:<20} {exp_val:>10.2f}  {model_val:>10.2f}  "
                  f"{abs_err:>+10.2f}  {within:>8}")


def save_calibration_report(output_dir: str, report_data: Dict):
    """
    Save detailed calibration report to JSON.
    
    Args:
        output_dir: Output directory path
        report_data: Calibration report data
    """
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, 'calibration_report.json')
    
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n✓ Calibration report saved to: {output_file}")


def main():
    """
    Main calibration workflow.
    """
    print(f"\n{'#'*80}")
    print("PHASE 5: BASELINE MODEL CALIBRATION")
    print("Comparison with Experimental XRD/TGA Data (28 days)")
    print(f"{'#'*80}")
    
    # Define paths
    project_root = Path(__file__).parent.parent
    exp_data_path = project_root / 'validation' / 'experimental_data_28d.json'
    model_data_path = project_root / 'outputs' / 'baseline_28d.json'
    output_dir = project_root / 'validation' / 'calibration_results'
    
    try:
        # Load data
        exp_data = load_experimental_data(str(exp_data_path))
        model_data = load_baseline_model(str(model_data_path))
        
        # Extract phase assemblages
        exp_phases = extract_experimental_phases(exp_data)
        model_phases = extract_model_phases(model_data)
        
        print(f"\n✓ Extracted {len(exp_phases)} experimental phases")
        print(f"✓ Extracted {len(model_phases)} model phases")
        
        # Map phase names
        phase_map = map_phase_names(exp_phases, model_phases)
        
        # Calculate errors
        errors = calculate_phase_errors(exp_phases, model_phases, phase_map)
        
        # Calculate overall metrics
        metrics = calculate_overall_metrics(errors)
        
        # Compare pore solution
        ps_comparison = compare_pore_solution(exp_data, model_data)
        
        # Generate recommendations
        recommendations = generate_calibration_recommendations(errors, metrics)
        
        # Print results
        print_comparison_table(errors)
        
        print(f"\n{'='*80}")
        print("OVERALL CALIBRATION METRICS")
        print(f"{'='*80}")
        print(f"Mean Absolute Error (MAE):     {metrics['mean_absolute_error_wt_percent']:.3f} wt%")
        print(f"Root Mean Square Error (RMSE): {metrics['root_mean_square_error_wt_percent']:.3f} wt%")
        print(f"Mean Relative Error:           {metrics['mean_relative_error_percent']:.1f}%")
        print(f"Phases within uncertainty:     {metrics['phases_within_uncertainty']}/{metrics['total_phases_compared']}")
        print(f"Calibration quality:           {metrics['calibration_quality_percent']:.1f}%")
        
        print(f"\n{'='*80}")
        print("PORE SOLUTION COMPARISON")
        print(f"{'='*80}")
        print(f"pH:  Exp={ps_comparison['pH']['experimental']:.2f}, "
              f"Model={ps_comparison['pH']['model']:.2f}, "
              f"Error={ps_comparison['pH']['error']:+.2f}")
        
        print(f"\n{'='*80}")
        print("CALIBRATION RECOMMENDATIONS")
        print(f"{'='*80}")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        # Prepare report data
        report_data = {
            'calibration_info': {
                'description': 'Phase 5 calibration: baseline model vs experimental data',
                'experimental_data_source': str(exp_data_path),
                'model_data_source': str(model_data_path),
                'calibration_date': '2026-02-28',
                'temperature_C': 20,
                'age_days': 28
            },
            'phase_errors': errors,
            'overall_metrics': metrics,
            'pore_solution_comparison': ps_comparison,
            'recommendations': recommendations,
            'calibration_status': 'PASS' if metrics['calibration_quality_percent'] >= 70 else 'NEEDS_ADJUSTMENT'
        }
        
        # Save report
        save_calibration_report(str(output_dir), report_data)
        
        print(f"\n{'='*80}")
        print("CALIBRATION COMPLETE")
        print(f"{'='*80}")
        
        # Return success/failure code
        if metrics['calibration_quality_percent'] >= 70:
            print("✓ CALIBRATION STATUS: PASS (quality ≥70%)")
            print("  Model predictions are in good agreement with experimental data.")
            print("  Baseline model is suitable for Phase 4 degradation simulations.")
            return 0
        else:
            print("⚠ CALIBRATION STATUS: NEEDS ADJUSTMENT (quality <70%)")
            print("  Model predictions deviate from experimental data.")
            print("  Review recommendations and adjust model parameters before Phase 4.")
            return 1
    
    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}")
        print("  Please ensure all required files exist:")
        print(f"  - {exp_data_path}")
        print(f"  - {model_data_path}")
        return 2
    
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == '__main__':
    sys.exit(main())
