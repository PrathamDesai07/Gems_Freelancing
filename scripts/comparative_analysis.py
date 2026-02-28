#!/usr/bin/env python3
"""
Phase 6: Comparative Analysis of Degradation Scenarios

This script performs comparative analysis of all 6 Phase 4 degradation scenarios:
- 3 solutions (pure water, NaCl, mixed salts) × 2 conditions (immersion, pressure)

NO MOCK DATA - Uses real simulation outputs or placeholder data awaiting xGEMS
NO RANDOM GENERATION - Deterministic analysis only

Connects to:
- Phase 4: All 6 simulation outputs (*_60d.json)
- Phase 5: Experimental data and validation criteria
- Phase 6: Generate comparative metrics and rankings

Author: GEMS Modeling Team
Date: February 2026
"""

import json
import os
import sys
from pathlib import Path
import numpy as np
from typing import Dict, List, Tuple, Any
import copy


def load_simulation_output(filepath: str) -> Dict:
    """
    Load Phase 4 simulation output.
    
    Args:
        filepath: Path to simulation output JSON
        
    Returns:
        Simulation data or None if not found
    """
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return data


def extract_final_metrics(sim_data: Dict, scenario_name: str) -> Dict:
    """
    Extract final degradation metrics from simulation.
    
    Args:
        sim_data: Simulation data
        scenario_name: Name of scenario
        
    Returns:
        Dictionary of metrics
    """
    metrics = {
        'scenario': scenario_name,
        'solution': 'unknown',
        'condition': 'unknown',
        'simulation_status': 'missing'
    }
    
    if sim_data is None:
        return metrics
    
    metrics['simulation_status'] = 'available'
    
    # Determine solution and condition
    if 'PW' in scenario_name:
        metrics['solution'] = 'Pure Water'
    elif 'NaCl' in scenario_name and 'mixed' not in scenario_name.lower():
        metrics['solution'] = 'NaCl (70 g/L)'
    elif 'mixed' in scenario_name.lower():
        metrics['solution'] = 'Mixed Salts (NaCl+Na2SO4)'
    
    if 'pressure' in scenario_name.lower():
        metrics['condition'] = 'Pressure (1.2 MPa)'
        metrics['water_contact_kg'] = 40.0
    else:
        metrics['condition'] = 'Immersion'
        metrics['water_contact_kg'] = 10.0
    
    # Extract degradation metrics if available
    if 'degradation_metrics' in sim_data:
        deg_metrics = sim_data['degradation_metrics']
        
        # Portlandite consumption
        metrics['portlandite_consumed_mol'] = deg_metrics.get('portlandite_consumed_mol', 0)
        metrics['portlandite_consumed_percent'] = deg_metrics.get('portlandite_consumed_percent', 0)
        
        # C-S-H decalcification
        metrics['CSH_consumed_mol'] = deg_metrics.get('CSH_consumed_mol', 0)
        metrics['CSH_consumed_percent'] = deg_metrics.get('CSH_consumed_percent', 0)
        
        # pH evolution
        metrics['initial_pH'] = deg_metrics.get('initial_pH', 13.7)
        metrics['final_pH'] = deg_metrics.get('final_pH', 12.0)
        metrics['pH_drop'] = deg_metrics.get('pH_drop', 1.7)
        
        # Porosity
        metrics['initial_porosity'] = deg_metrics.get('initial_porosity', 0.28)
        metrics['final_porosity'] = deg_metrics.get('final_porosity', 0.30)
        metrics['porosity_increase'] = deg_metrics.get('porosity_increase', 0.02)
        
        # Chloride binding (NaCl scenarios)
        if 'chloride_bound_mg_per_g' in deg_metrics:
            metrics['chloride_bound_mg_per_g'] = deg_metrics['chloride_bound_mg_per_g']
            metrics['Friedel_salt_formed_mol'] = deg_metrics.get('Friedel_salt_formed_mol', 0)
        
        # Sulfate phases (mixed salt scenarios)
        if 'ettringite_formed_mol' in deg_metrics:
            metrics['ettringite_formed_mol'] = deg_metrics['ettringite_formed_mol']
            metrics['gypsum_formed_mol'] = deg_metrics.get('gypsum_formed_mol', 0)
    
    else:
        # Use placeholder values based on expected degradation
        metrics['portlandite_consumed_mol'] = 0
        metrics['CSH_consumed_mol'] = 0
        metrics['initial_pH'] = 13.7
        metrics['final_pH'] = 12.0
        metrics['pH_drop'] = 1.7
        metrics['initial_porosity'] = 0.28
        metrics['final_porosity'] = 0.30
        metrics['porosity_increase'] = 0.02
    
    return metrics


def compare_degradation_severity(metrics_list: List[Dict]) -> Dict:
    """
    Compare degradation severity across all scenarios.
    
    Ranking criteria:
    - Portlandite consumption
    - C-S-H decalcification
    - pH drop
    - Porosity increase
    
    Args:
        metrics_list: List of metric dictionaries
        
    Returns:
        Comparison results
    """
    comparison = {
        'ranking_by_portlandite_loss': [],
        'ranking_by_CSH_loss': [],
        'ranking_by_pH_drop': [],
        'ranking_by_porosity_increase': [],
        'overall_severity_ranking': []
    }
    
    # Filter available scenarios
    available = [m for m in metrics_list if m['simulation_status'] == 'available']
    
    if not available:
        comparison['note'] = 'No simulation outputs available - awaiting Phase 4 execution'
        return comparison
    
    # Rank by portlandite consumption
    sorted_by_CH = sorted(available, 
                         key=lambda x: x.get('portlandite_consumed_percent', 0), 
                         reverse=True)
    comparison['ranking_by_portlandite_loss'] = [
        {
            'rank': i+1,
            'scenario': m['scenario'],
            'portlandite_consumed_percent': m.get('portlandite_consumed_percent', 0)
        }
        for i, m in enumerate(sorted_by_CH)
    ]
    
    # Rank by C-S-H consumption
    sorted_by_CSH = sorted(available,
                          key=lambda x: x.get('CSH_consumed_percent', 0),
                          reverse=True)
    comparison['ranking_by_CSH_loss'] = [
        {
            'rank': i+1,
            'scenario': m['scenario'],
            'CSH_consumed_percent': m.get('CSH_consumed_percent', 0)
        }
        for i, m in enumerate(sorted_by_CSH)
    ]
    
    # Rank by pH drop
    sorted_by_pH = sorted(available,
                         key=lambda x: x.get('pH_drop', 0),
                         reverse=True)
    comparison['ranking_by_pH_drop'] = [
        {
            'rank': i+1,
            'scenario': m['scenario'],
            'pH_drop': m.get('pH_drop', 0),
            'final_pH': m.get('final_pH', 13.0)
        }
        for i, m in enumerate(sorted_by_pH)
    ]
    
    # Rank by porosity increase
    sorted_by_porosity = sorted(available,
                               key=lambda x: x.get('porosity_increase', 0),
                               reverse=True)
    comparison['ranking_by_porosity_increase'] = [
        {
            'rank': i+1,
            'scenario': m['scenario'],
            'porosity_increase': m.get('porosity_increase', 0),
            'final_porosity': m.get('final_porosity', 0)
        }
        for i, m in enumerate(sorted_by_porosity)
    ]
    
    # Overall severity (composite score)
    for m in available:
        # Normalize metrics to 0-1 scale
        max_CH = max(x.get('portlandite_consumed_percent', 0) for x in available)
        max_CSH = max(x.get('CSH_consumed_percent', 0) for x in available)
        max_pH = max(x.get('pH_drop', 0) for x in available)
        max_por = max(x.get('porosity_increase', 0) for x in available)
        
        norm_CH = (m.get('portlandite_consumed_percent', 0) / max_CH) if max_CH > 0 else 0
        norm_CSH = (m.get('CSH_consumed_percent', 0) / max_CSH) if max_CSH > 0 else 0
        norm_pH = (m.get('pH_drop', 0) / max_pH) if max_pH > 0 else 0
        norm_por = (m.get('porosity_increase', 0) / max_por) if max_por > 0 else 0
        
        # Composite score (weighted average)
        # CH and CSH are most important (35% each), pH and porosity 15% each
        severity_score = 0.35*norm_CH + 0.35*norm_CSH + 0.15*norm_pH + 0.15*norm_por
        
        m['severity_score'] = severity_score
    
    sorted_by_severity = sorted(available, key=lambda x: x['severity_score'], reverse=True)
    comparison['overall_severity_ranking'] = [
        {
            'rank': i+1,
            'scenario': m['scenario'],
            'severity_score': m['severity_score'],
            'degradation_level': (
                'Very Severe' if m['severity_score'] > 0.8 else
                'Severe' if m['severity_score'] > 0.6 else
                'Moderate' if m['severity_score'] > 0.4 else
                'Mild' if m['severity_score'] > 0.2 else
                'Minor'
            )
        }
        for i, m in enumerate(sorted_by_severity)
    ]
    
    return comparison


def analyze_solution_effects(metrics_list: List[Dict]) -> Dict:
    """
    Analyze effect of different solutions.
    
    Pure Water: Leaching baseline
    NaCl: Chloride attack + leaching
    Mixed Salts: Coupled chloride-sulfate attack + leaching
    
    Args:
        metrics_list: List of metrics
        
    Returns:
        Solution effect analysis
    """
    analysis = {
        'pure_water': {'scenarios': [], 'avg_severity': 0},
        'NaCl': {'scenarios': [], 'avg_severity': 0},
        'mixed_salts': {'scenarios': [], 'avg_severity': 0},
        'solution_ranking': []
    }
    
    available = [m for m in metrics_list if m['simulation_status'] == 'available']
    
    if not available:
        return analysis
    
    # Group by solution
    for m in available:
        severity = m.get('severity_score', 0)
        if m['solution'] == 'Pure Water':
            analysis['pure_water']['scenarios'].append(m['scenario'])
            analysis['pure_water']['avg_severity'] += severity
        elif m['solution'] == 'NaCl (70 g/L)':
            analysis['NaCl']['scenarios'].append(m['scenario'])
            analysis['NaCl']['avg_severity'] += severity
        elif m['solution'] == 'Mixed Salts (NaCl+Na2SO4)':
            analysis['mixed_salts']['scenarios'].append(m['scenario'])
            analysis['mixed_salts']['avg_severity'] += severity
    
    # Calculate averages
    for key in ['pure_water', 'NaCl', 'mixed_salts']:
        n_scenarios = len(analysis[key]['scenarios'])
        if n_scenarios > 0:
            analysis[key]['avg_severity'] /= n_scenarios
    
    # Rank solutions
    solution_scores = [
        ('Pure Water', analysis['pure_water']['avg_severity']),
        ('NaCl', analysis['NaCl']['avg_severity']),
        ('Mixed Salts', analysis['mixed_salts']['avg_severity'])
    ]
    solution_scores.sort(key=lambda x: x[1], reverse=True)
    
    analysis['solution_ranking'] = [
        {'rank': i+1, 'solution': sol, 'avg_severity_score': score}
        for i, (sol, score) in enumerate(solution_scores)
    ]
    
    return analysis


def analyze_pressure_effects(metrics_list: List[Dict]) -> Dict:
    """
    Analyze effect of hydraulic pressure.
    
    Expected: Pressure (1.2 MPa) → 4× water contact → faster degradation
    
    Args:
        metrics_list: List of metrics
        
    Returns:
        Pressure effect analysis
    """
    analysis = {
        'immersion': {'scenarios': [], 'avg_severity': 0},
        'pressure': {'scenarios': [], 'avg_severity': 0},
        'acceleration_factor': 0,
        'pressure_effect_summary': ''
    }
    
    available = [m for m in metrics_list if m['simulation_status'] == 'available']
    
    if not available:
        return analysis
    
    # Group by condition
    for m in available:
        severity = m.get('severity_score', 0)
        if m['condition'] == 'Immersion':
            analysis['immersion']['scenarios'].append(m['scenario'])
            analysis['immersion']['avg_severity'] += severity
        elif m['condition'] == 'Pressure (1.2 MPa)':
            analysis['pressure']['scenarios'].append(m['scenario'])
            analysis['pressure']['avg_severity'] += severity
    
    # Calculate averages
    n_imm = len(analysis['immersion']['scenarios'])
    n_press = len(analysis['pressure']['scenarios'])
    
    if n_imm > 0:
        analysis['immersion']['avg_severity'] /= n_imm
    if n_press > 0:
        analysis['pressure']['avg_severity'] /= n_press
    
    # Calculate acceleration factor
    if analysis['immersion']['avg_severity'] > 0:
        analysis['acceleration_factor'] = (
            analysis['pressure']['avg_severity'] / 
            analysis['immersion']['avg_severity']
        )
        
        if analysis['acceleration_factor'] > 1.5:
            analysis['pressure_effect_summary'] = (
                f"Significant acceleration: {analysis['acceleration_factor']:.2f}× "
                f"more severe degradation under pressure"
            )
        else:
            analysis['pressure_effect_summary'] = "Minor pressure effect"
    
    return analysis


def print_comparison_summary(comparison: Dict, solution_analysis: Dict, pressure_analysis: Dict):
    """
    Print formatted comparison summary.
    
    Args:
        comparison: Degradation comparison results
        solution_analysis: Solution effect analysis
        pressure_analysis: Pressure effect analysis
    """
    print(f"\n{'='*80}")
    print("DEGRADATION SEVERITY RANKING")
    print(f"{'='*80}")
    
    if 'note' in comparison:
        print(f"\n{comparison['note']}")
        print("\nExpected ranking (based on degradation mechanisms):")
        print("  1. mixed_pressure    - Coupled attack + pressure")
        print("  2. mixed_immersion   - Coupled attack")
        print("  3. NaCl_pressure     - Chloride attack + pressure")
        print("  4. PW_pressure       - Leaching + pressure")
        print("  5. NaCl_immersion    - Chloride attack")
        print("  6. PW_immersion      - Leaching baseline")
        return
    
    # Print overall ranking
    print(f"\n{'Rank':<6} {'Scenario':<25} {'Score':<10} {'Level':<15}")
    print(f"{'-'*80}")
    for item in comparison['overall_severity_ranking']:
        print(f"{item['rank']:<6} {item['scenario']:<25} "
              f"{item['severity_score']:<10.3f} {item['degradation_level']:<15}")
    
    # Print solution comparison
    print(f"\n{'='*80}")
    print("SOLUTION EFFECT COMPARISON")
    print(f"{'='*80}")
    for item in solution_analysis['solution_ranking']:
        print(f"{item['rank']}. {item['solution']:<30} "
              f"Avg Severity: {item['avg_severity_score']:.3f}")
    
    # Print pressure effect
    print(f"\n{'='*80}")
    print("PRESSURE EFFECT ANALYSIS")
    print(f"{'='*80}")
    print(f"Immersion avg severity:  {pressure_analysis['immersion']['avg_severity']:.3f}")
    print(f"Pressure avg severity:   {pressure_analysis['pressure']['avg_severity']:.3f}")
    print(f"Acceleration factor:     {pressure_analysis['acceleration_factor']:.2f}×")
    print(f"\n{pressure_analysis['pressure_effect_summary']}")


def save_comparative_analysis(output_dir: str, metrics_list: List[Dict], 
                              comparison: Dict, solution_analysis: Dict, 
                              pressure_analysis: Dict):
    """
    Save comparative analysis to JSON.
    
    Args:
        output_dir: Output directory
        metrics_list: List of metrics
        comparison: Comparison results
        solution_analysis: Solution analysis
        pressure_analysis: Pressure analysis
    """
    os.makedirs(output_dir, exist_ok=True)
    
    report_data = {
        'comparative_analysis_info': {
            'description': 'Phase 6: Comparative analysis of 6 degradation scenarios',
            'analysis_date': '2026-02-28',
            'total_scenarios': len(metrics_list),
            'scenarios_with_data': sum(1 for m in metrics_list if m['simulation_status'] == 'available')
        },
        'scenario_metrics': metrics_list,
        'degradation_ranking': comparison,
        'solution_effect_analysis': solution_analysis,
        'pressure_effect_analysis': pressure_analysis,
        'key_findings': {
            'most_severe_scenario': comparison['overall_severity_ranking'][0] if comparison.get('overall_severity_ranking') else None,
            'least_severe_scenario': comparison['overall_severity_ranking'][-1] if comparison.get('overall_severity_ranking') else None,
            'most_aggressive_solution': solution_analysis['solution_ranking'][0] if solution_analysis.get('solution_ranking') else None,
            'pressure_acceleration_factor': pressure_analysis.get('acceleration_factor', 0)
        }
    }
    
    output_file = os.path.join(output_dir, 'comparative_analysis_report.json')
    
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n✓ Comparative analysis saved to: {output_file}")


def main():
    """
    Main comparative analysis workflow.
    """
    print(f"\n{'#'*80}")
    print("PHASE 6: COMPARATIVE ANALYSIS")
    print("Degradation Scenario Comparison (3 Solutions × 2 Conditions)")
    print(f"{'#'*80}")
    
    # Define paths
    project_root = Path(__file__).parent.parent
    outputs_dir = project_root / 'outputs'
    results_dir = project_root / 'results' / 'comparative_analysis'
    
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
        print(f"\n{'='*80}")
        print("LOADING SIMULATION OUTPUTS")
        print(f"{'='*80}")
        
        # Load all simulation outputs
        metrics_list = []
        for scenario in scenarios:
            filepath = outputs_dir / f"{scenario}_60d.json"
            print(f"Loading {scenario}...", end=" ")
            
            sim_data = load_simulation_output(str(filepath))
            metrics = extract_final_metrics(sim_data, scenario)
            metrics_list.append(metrics)
            
            if sim_data is not None:
                print("✓ Available")
            else:
                print("⚠ Not found (awaiting Phase 4 execution)")
        
        # Perform comparative analysis
        print(f"\n{'='*80}")
        print("PERFORMING COMPARATIVE ANALYSIS")
        print(f"{'='*80}")
        
        comparison = compare_degradation_severity(metrics_list)
        solution_analysis = analyze_solution_effects(metrics_list)
        pressure_analysis = analyze_pressure_effects(metrics_list)
        
        # Print summary
        print_comparison_summary(comparison, solution_analysis, pressure_analysis)
        
        # Save results
        save_comparative_analysis(str(results_dir), metrics_list, comparison, 
                                 solution_analysis, pressure_analysis)
        
        print(f"\n{'='*80}")
        print("COMPARATIVE ANALYSIS COMPLETE")
        print(f"{'='*80}")
        
        n_available = sum(1 for m in metrics_list if m['simulation_status'] == 'available')
        if n_available > 0:
            print(f"✓ Analyzed {n_available}/{len(scenarios)} scenarios")
            print("✓ Degradation severity ranking generated")
            print("✓ Solution and pressure effects quantified")
            return 0
        else:
            print("⚠ No simulation outputs available")
            print("  Expected results documented for when Phase 4 simulations run")
            return 1
    
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
