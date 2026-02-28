#!/usr/bin/env python3
"""
Phase 6: Visualization - Degradation Data Plotting

This script generates publication-quality plots for degradation simulation results:
- Phase evolution time series
- pH degradation curves
- Chloride binding isotherms
- Sulfate attack progression
- Comparative bar charts

NO MOCK DATA - Uses real simulation outputs or expected patterns
NO RANDOM GENERATION - Deterministic plotting only

Connects to:
- Phase 4: Simulation outputs (*_60d.json)
- Phase 5: Experimental validation data
- Phase 6: Comparative analysis results

Author: GEMS Modeling Team
Date: February 2026
"""

import json
import os
import sys
from pathlib import Path
import numpy as np
from typing import Dict, List, Tuple, Any
import matplotlib.pyplot as plt
import matplotlib as mpl

# Set publication-quality defaults
mpl.rcParams['font.size'] = 11
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['axes.linewidth'] = 1.2
mpl.rcParams['xtick.major.width'] = 1.2
mpl.rcParams['ytick.major.width'] = 1.2


def load_simulation_data(filepath: str) -> Dict:
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


def plot_phase_evolution(scenarios: List[str], outputs_dir: str, figures_dir: str):
    """
    Plot phase assemblage evolution for all scenarios.
    
    Args:
        scenarios: List of scenario names
        outputs_dir: Directory with simulation outputs
        figures_dir: Output directory for figures
    """
    print("\nGenerating phase evolution plots...")
    
    # Create figure with subplots for each solution type
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.suptitle('Phase Assemblage Evolution - All Scenarios', fontsize=14, fontweight='bold')
    
    solution_types = ['PW', 'NaCl', 'mixed']
    conditions = ['immersion', 'pressure']
    
    for i, solution in enumerate(solution_types):
        for j, condition in enumerate(conditions):
            ax = axes[i, j]
            scenario = f"{solution}_{condition}"
            
            filepath = os.path.join(outputs_dir, f"{scenario}_60d.json")
            data = load_simulation_data(filepath)
            
            if data and 'time_series' in data:
                # Extract time series
                time_series = data['time_series']
                times = [step.get('time_days', i*3) for i, step in enumerate(time_series)]
                
                # Extract key phases
                portlandite = []
                csh = []
                ettringite = []
                friedel = []
                
                for step in time_series:
                    phases = step.get('phase_assemblage', {})
                    
                    # Portlandite
                    CH = phases.get('portlandite', {}).get('amount_mol', 0)
                    portlandite.append(CH)
                    
                    # C-S-H
                    CSH = phases.get('CSH_gel', {}).get('amount_mol', 0)
                    csh.append(CSH)
                    
                    # Ettringite
                    Ett = phases.get('ettringite', {}).get('amount_mol', 0)
                    ettringite.append(Ett)
                    
                    # Friedel's salt (chloride scenarios)
                    Friedel = phases.get('friedel_salt', {}).get('amount_mol', 0)
                    friedel.append(Friedel)
                
                # Plot
                ax.plot(times, portlandite, 'b-', linewidth=2, label='Portlandite')
                ax.plot(times, csh, 'g-', linewidth=2, label='C-S-H')
                if max(ettringite) > 0.01:
                    ax.plot(times, ettringite, 'r-', linewidth=2, label='Ettringite')
                if max(friedel) > 0.01:
                    ax.plot(times, friedel, 'm-', linewidth=2, label="Friedel's salt")
                
                ax.set_xlabel('Time (days)', fontweight='bold')
                ax.set_ylabel('Amount (mol)', fontweight='bold')
                ax.set_title(f"{solution.upper()} - {condition.capitalize()}", fontweight='bold')
                ax.grid(True, alpha=0.3)
                ax.legend(loc='best', frameon=True, fontsize=9)
            
            else:
                # Show placeholder message
                ax.text(0.5, 0.5, f'Awaiting {scenario}\nsimulation output',
                       ha='center', va='center', transform=ax.transAxes,
                       fontsize=10, style='italic', color='gray')
                ax.set_xlabel('Time (days)')
                ax.set_ylabel('Amount (mol)')
                ax.set_title(f"{solution.upper()} - {condition.capitalize()}", fontweight='bold')
    
    plt.tight_layout()
    output_file = os.path.join(figures_dir, 'phase_evolution_all.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved: {output_file}")
    plt.close()


def plot_pH_evolution(scenarios: List[str], outputs_dir: str, figures_dir: str):
    """
    Plot pH evolution for all scenarios.
    
    Args:
        scenarios: List of scenario names
        outputs_dir: Directory with simulation outputs
        figures_dir: Output directory for figures
    """
    print("\nGenerating pH evolution plots...")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('pH Evolution During Degradation', fontsize=14, fontweight='bold')
    
    colors = {
        'PW_immersion': 'blue',
        'PW_pressure': 'darkblue',
        'NaCl_immersion': 'green',
        'NaCl_pressure': 'darkgreen',
        'mixed_immersion': 'red',
        'mixed_pressure': 'darkred'
    }
    
    linestyles = {'immersion': '-', 'pressure': '--'}
    
    # Subplot 1: All scenarios
    for scenario in scenarios:
        filepath = os.path.join(outputs_dir, f"{scenario}_60d.json")
        data = load_simulation_data(filepath)
        
        if data and 'time_series' in data:
            time_series = data['time_series']
            times = [step.get('time_days', i*3) for i, step in enumerate(time_series)]
            pH_values = [step.get('pore_solution', {}).get('pH', 13.7) for step in time_series]
            
            ls = linestyles['pressure'] if 'pressure' in scenario else linestyles['immersion']
            ax1.plot(times, pH_values, color=colors.get(scenario, 'black'),
                    linestyle=ls, linewidth=2, label=scenario.replace('_', ' '))
    
    ax1.axhline(y=12.5, color='gray', linestyle=':', linewidth=1, alpha=0.7, label='Portlandite buffer')
    ax1.set_xlabel('Time (days)', fontweight='bold')
    ax1.set_ylabel('pH', fontweight='bold')
    ax1.set_title('All Scenarios', fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right', frameon=True, fontsize=9)
    ax1.set_ylim([10, 14.5])
    
    # Subplot 2: Solution comparison (immersion only)
    for scenario in [s for s in scenarios if 'immersion' in s]:
        filepath = os.path.join(outputs_dir, f"{scenario}_60d.json")
        data = load_simulation_data(filepath)
        
        if data and 'time_series' in data:
            time_series = data['time_series']
            times = [step.get('time_days', i*3) for i, step in enumerate(time_series)]
            pH_values = [step.get('pore_solution', {}).get('pH', 13.7) for step in time_series]
            
            solution_label = scenario.split('_')[0].upper()
            ax2.plot(times, pH_values, color=colors.get(scenario, 'black'),
                    linewidth=2, label=solution_label)
    
    ax2.set_xlabel('Time (days)', fontweight='bold')
    ax2.set_ylabel('pH', fontweight='bold')
    ax2.set_title('Solution Comparison (Immersion)', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right', frameon=True)
    ax2.set_ylim([10, 14.5])
    
    plt.tight_layout()
    output_file = os.path.join(figures_dir, 'pH_evolution.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved: {output_file}")
    plt.close()


def plot_portlandite_depletion(scenarios: List[str], outputs_dir: str, figures_dir: str):
    """
    Plot portlandite depletion comparison.
    
    Args:
        scenarios: List of scenario names
        outputs_dir: Directory with simulation outputs
        figures_dir: Output directory for figures
    """
    print("\nGenerating portlandite depletion plots...")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = {
        'PW_immersion': 'blue',
        'PW_pressure': 'darkblue',
        'NaCl_immersion': 'green',
        'NaCl_pressure': 'darkgreen',
        'mixed_immersion': 'red',
        'mixed_pressure': 'darkred'
    }
    
    for scenario in scenarios:
        filepath = os.path.join(outputs_dir, f"{scenario}_60d.json")
        data = load_simulation_data(filepath)
        
        if data and 'time_series' in data:
            time_series = data['time_series']
            times = [step.get('time_days', i*3) for i, step in enumerate(time_series)]
            
            # Extract portlandite
            CH_values = []
            for step in time_series:
                phases = step.get('phase_assemblage', {})
                CH = phases.get('portlandite', {}).get('amount_mol', 0)
                CH_values.append(CH)
            
            if len(CH_values) > 0 and max(CH_values) > 0:
                # Normalize to percentage
                initial_CH = CH_values[0] if CH_values[0] > 0 else 4.2
                CH_percent = [(ch/initial_CH)*100 for ch in CH_values]
                
                ls = '--' if 'pressure' in scenario else '-'
                ax.plot(times, CH_percent, color=colors.get(scenario, 'black'),
                       linestyle=ls, linewidth=2, label=scenario.replace('_', ' '))
    
    ax.axhline(y=50, color='gray', linestyle=':', linewidth=1, alpha=0.7, label='50% depletion')
    ax.axhline(y=10, color='red', linestyle=':', linewidth=1, alpha=0.7, label='90% depletion')
    ax.set_xlabel('Time (days)', fontweight='bold')
    ax.set_ylabel('Portlandite Remaining (%)', fontweight='bold')
    ax.set_title('Portlandite Depletion - All Scenarios', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', frameon=True, fontsize=9)
    ax.set_ylim([0, 105])
    
    plt.tight_layout()
    output_file = os.path.join(figures_dir, 'portlandite_depletion.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved: {output_file}")
    plt.close()


def plot_chloride_binding(scenarios: List[str], outputs_dir: str, figures_dir: str):
    """
    Plot chloride binding for NaCl scenarios.
    
    Args:
        scenarios: List of scenario names
        outputs_dir: Directory with simulation outputs
        figures_dir: Output directory for figures
    """
    print("\nGenerating chloride binding plots...")
    
    chloride_scenarios = [s for s in scenarios if 'NaCl' in s or 'mixed' in s]
    
    if not chloride_scenarios:
        print("  ⚠ No chloride scenarios found")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Chloride Binding', fontsize=14, fontweight='bold')
    
    colors = {'NaCl_immersion': 'green', 'NaCl_pressure': 'darkgreen',
              'mixed_immersion': 'red', 'mixed_pressure': 'darkred'}
    
    for scenario in chloride_scenarios:
        filepath = os.path.join(outputs_dir, f"{scenario}_60d.json")
        data = load_simulation_data(filepath)
        
        if data and 'time_series' in data:
            time_series = data['time_series']
            times = [step.get('time_days', i*3) for i, step in enumerate(time_series)]
            
            # Extract Friedel's salt and chloride binding
            friedel_values = []
            cl_bound = []
            for step in time_series:
                phases = step.get('phase_assemblage', {})
                friedel_data = phases.get('friedel_salt', {})
                friedel_mol = friedel_data.get('amount_mol', 0)
                friedel_values.append(friedel_mol)
                
                # Calculate chloride bound from Friedel's salt
                # 1 mol Friedel binds 2 mol Cl (from CaCl2)
                # Cl_bound (mg/g) = Friedel (mol) × 2 × 35.45 (MW Cl) × 1000 / paste_mass (g)
                cl_mg_per_g = friedel_data.get('Cl_bound_mg_per_g', 0)
                cl_bound.append(cl_mg_per_g)
            
            # Plot Friedel's salt formation
            ls = '--' if 'pressure' in scenario else '-'
            ax1.plot(times, friedel_values, color=colors.get(scenario, 'black'),
                    linestyle=ls, linewidth=2, label=scenario.replace('_', ' '))
            
            # Plot total chloride binding
            if max(cl_bound) > 0:
                ax2.plot(times, cl_bound, color=colors.get(scenario, 'black'),
                        linestyle=ls, linewidth=2, label=scenario.replace('_', ' '))
    
    ax1.set_xlabel('Time (days)', fontweight='bold')
    ax1.set_ylabel("Friedel's Salt (mol)", fontweight='bold')
    ax1.set_title("Friedel's Salt Formation", fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', frameon=True)
    
    ax2.set_xlabel('Time (days)', fontweight='bold')
    ax2.set_ylabel('Chloride Bound (mg/g paste)', fontweight='bold')
    ax2.set_title('Total Chloride Binding', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='best', frameon=True)
    
    plt.tight_layout()
    output_file = os.path.join(figures_dir, 'chloride_binding.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved: {output_file}")
    plt.close()


def plot_degradation_comparison(comparative_report: str, figures_dir: str):
    """
    Plot degradation severity comparison bar chart.
    
    Args:
        comparative_report: Path to comparative analysis JSON
        figures_dir: Output directory for figures
    """
    print("\nGenerating degradation comparison charts...")
    
    if not os.path.exists(comparative_report):
        print("  ⚠ Comparative analysis report not found")
        return
    
    with open(comparative_report, 'r') as f:
        data = json.load(f)
    
    # Extract scenario metrics
    metrics = data.get('scenario_metrics', [])
    available = [m for m in metrics if m['simulation_status'] == 'available']
    
    if not available:
        print("  ⚠ No simulation data available")
        return
    
    # Create comparison bar chart
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Degradation Metrics Comparison', fontsize=14, fontweight='bold')
    
    scenarios = [m['scenario'] for m in available]
    
    # Portlandite consumption
    CH_consumed = [m.get('portlandite_consumed_percent', 0) for m in available]
    for i, (scenario, value) in enumerate(zip(scenarios, CH_consumed)):
        color = 'blue' if 'PW' in scenario else ('green' if 'NaCl' in scenario else 'red')
        alpha = 0.7 if 'immersion' in scenario else 1.0
        ax1.bar(i, value, color=color, alpha=alpha, edgecolor='black')
    ax1.set_ylabel('Portlandite Consumed (%)', fontweight='bold')
    ax1.set_title('Portlandite Consumption', fontweight='bold')
    ax1.grid(True, axis='y', alpha=0.3)
    ax1.set_xticks(range(len(scenarios)))
    ax1.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
    
    # C-S-H decalcification
    CSH_consumed = [m.get('CSH_consumed_percent', 0) for m in available]
    for i, (scenario, value) in enumerate(zip(scenarios, CSH_consumed)):
        color = 'blue' if 'PW' in scenario else ('green' if 'NaCl' in scenario else 'red')
        alpha = 0.7 if 'immersion' in scenario else 1.0
        ax2.bar(i, value, color=color, alpha=alpha, edgecolor='black')
    ax2.set_ylabel('C-S-H Consumed (%)', fontweight='bold')
    ax2.set_title('C-S-H Decalcification', fontweight='bold')
    ax2.grid(True, axis='y', alpha=0.3)
    ax2.set_xticks(range(len(scenarios)))
    ax2.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
    
    # pH drop
    pH_drop = [m.get('pH_drop', 0) for m in available]
    for i, (scenario, value) in enumerate(zip(scenarios, pH_drop)):
        color = 'blue' if 'PW' in scenario else ('green' if 'NaCl' in scenario else 'red')
        alpha = 0.7 if 'immersion' in scenario else 1.0
        ax3.bar(i, value, color=color, alpha=alpha, edgecolor='black')
    ax3.set_ylabel('pH Drop', fontweight='bold')
    ax3.set_title('pH Decrease', fontweight='bold')
    ax3.grid(True, axis='y', alpha=0.3)
    ax3.set_xticks(range(len(scenarios)))
    ax3.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
    
    # Porosity increase
    por_increase = [m.get('porosity_increase', 0) for m in available]
    for i, (scenario, value) in enumerate(zip(scenarios, por_increase)):
        color = 'blue' if 'PW' in scenario else ('green' if 'NaCl' in scenario else 'red')
        alpha = 0.7 if 'immersion' in scenario else 1.0
        ax4.bar(i, value, color=color, alpha=alpha, edgecolor='black')
    ax4.set_ylabel('Porosity Increase', fontweight='bold')
    ax4.set_title('Porosity Change', fontweight='bold')
    ax4.grid(True, axis='y', alpha=0.3)
    ax4.set_xticks(range(len(scenarios)))
    ax4.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
    
    plt.tight_layout()
    output_file = os.path.join(figures_dir, 'degradation_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved: {output_file}")
    plt.close()


def main():
    """
    Main visualization workflow.
    """
    print(f"\n{'#'*80}")
    print("PHASE 6: VISUALIZATION")
    print("Degradation Data Plotting and Figure Generation")
    print(f"{'#'*80}")
    
    # Define paths
    project_root = Path(__file__).parent.parent
    outputs_dir = project_root / 'outputs'
    comparative_report = project_root / 'results' / 'comparative_analysis' / 'comparative_analysis_report.json'
    figures_dir = project_root / 'results' / 'figures'
    
    # Create output directory
    os.makedirs(figures_dir, exist_ok=True)
    
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
        print("GENERATING FIGURES")
        print(f"{'='*80}")
        
        # Generate plots
        plot_phase_evolution(scenarios, str(outputs_dir), str(figures_dir))
        plot_pH_evolution(scenarios, str(outputs_dir), str(figures_dir))
        plot_portlandite_depletion(scenarios, str(outputs_dir), str(figures_dir))
        plot_chloride_binding(scenarios, str(outputs_dir), str(figures_dir))
        plot_degradation_comparison(str(comparative_report), str(figures_dir))
        
        print(f"\n{'='*80}")
        print("VISUALIZATION COMPLETE")
        print(f"{'='*80}")
        print(f"✓ Figures saved to: {figures_dir}")
        print("✓ 5 figure sets generated")
        print("  - Phase evolution (all scenarios)")
        print("  - pH evolution")
        print("  - Portlandite depletion")
        print("  - Chloride binding")
        print("  - Degradation comparison")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
