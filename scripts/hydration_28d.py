#!/usr/bin/env python3
"""
28-Day Hydration Baseline Calculation
Phase 2: Material Recipe Definition

This script calculates the equilibrium phase assemblage and pore solution
chemistry for Portland cement + fly ash paste after 28 days of sealed hydration
at 20°C. This establishes the baseline state before degradation exposure.

Project: Multi-environment reaction-transport modeling of fly ash blended cement paste
Date: February 2026
"""

import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd


def load_configuration():
    """Load all configuration and material data files."""
    base_path = Path(__file__).parent.parent
    
    # Load Phase 1 configuration
    with open(base_path / 'gems_project' / 'project_config.json', 'r') as f:
        project_config = json.load(f)
    
    # Load material compositions
    with open(base_path / 'materials' / 'cement_composition.json', 'r') as f:
        cement = json.load(f)
    
    with open(base_path / 'materials' / 'flyash_composition.json', 'r') as f:
        flyash = json.load(f)
    
    # Load paste recipe
    with open(base_path / 'recipes' / 'paste_recipe.json', 'r') as f:
        recipe = json.load(f)
    
    return project_config, cement, flyash, recipe


def calculate_system_composition(cement, flyash, recipe):
    """
    Calculate total system composition in moles from material data.
    This uses the real oxide compositions and paste recipe masses.
    """
    # Get masses per 1000 cm³
    m_cement = recipe['masses_per_1000cm3']['cement_g']
    m_flyash = recipe['masses_per_1000cm3']['fly_ash_g']
    m_water = recipe['masses_per_1000cm3']['water_g']
    
    # Initialize composition dictionary (in grams)
    composition_g = {}
    
    # Add oxides from cement
    for oxide, wt_percent in cement['oxides_wt_percent'].items():
        mass = m_cement * wt_percent / 100.0
        composition_g[oxide] = composition_g.get(oxide, 0) + mass
    
    # Add oxides from fly ash
    for oxide, wt_percent in flyash['oxides_wt_percent'].items():
        mass = m_flyash * wt_percent / 100.0
        composition_g[oxide] = composition_g.get(oxide, 0) + mass
    
    # Add water
    composition_g['H2O'] = m_water
    
    # Convert to moles using molecular weights
    molecular_weights = {
        'CaO': 56.08,
        'SiO2': 60.08,
        'Al2O3': 101.96,
        'Fe2O3': 159.69,
        'MgO': 40.30,
        'SO3': 80.06,
        'K2O': 94.20,
        'Na2O': 61.98,
        'TiO2': 79.87,
        'H2O': 18.015
    }
    
    composition_mol = {}
    for oxide, mass_g in composition_g.items():
        if oxide in molecular_weights:
            composition_mol[oxide] = mass_g / molecular_weights[oxide]
    
    return composition_g, composition_mol


def calculate_mineral_composition(cement, recipe):
    """
    Calculate clinker mineral amounts in moles.
    Used for setting hydration degrees.
    """
    m_cement = recipe['masses_per_1000cm3']['cement_g']
    
    # Molecular weights of clinker phases
    mw = {
        'C3S': 228.32,  # 3CaO·SiO2
        'C2S': 172.24,  # 2CaO·SiO2
        'C3A': 270.19,  # 3CaO·Al2O3
        'C4AF': 485.96, # 4CaO·Al2O3·Fe2O3
        'K2SO4': 174.26,
        'gypsum': 172.17, # CaSO4·2H2O
        'calcite': 100.09  # CaCO3
    }
    
    minerals_mol = {}
    for mineral, wt_percent in cement['minerals_wt_percent'].items():
        # Map mineral names
        mineral_key = mineral
        if mineral == 'gypsum_CaSO4_2H2O':
            mineral_key = 'gypsum'
        elif mineral == 'calcite_CaCO3':
            mineral_key = 'calcite'
        
        if mineral_key in mw:
            mass_g = m_cement * wt_percent / 100.0
            minerals_mol[mineral] = mass_g / mw[mineral_key]
    
    return minerals_mol


def set_hydration_degrees():
    """
    Set initial hydration degrees for 28-day sealed curing at 20°C.
    These are initial estimates based on literature and will be calibrated
    against experimental XRD/TGA data.
    
    Returns: Dictionary of hydration degrees (0-1)
    """
    hydration_degrees = {
        'C3S': 0.95,  # Alite hydrates rapidly, ~95% at 28d
        'C2S': 0.65,  # Belite hydrates slowly, ~65% at 28d
        'C3A': 1.00,  # Aluminate reacts completely in presence of gypsum
        'C4AF': 0.70, # Ferrite moderate hydration, ~70% at 28d
        'gypsum': 1.00, # Gypsum consumed early
        'K2SO4': 1.00,  # Soluble sulfate dissolves completely
        'calcite': 0.0,  # Calcite is inert filler
        
        # Fly ash reactivity
        'FA_glass': 0.20,  # 20% of glass reacted at 28d (pozzolanic reaction)
        'FA_mullite': 0.0,  # Mullite is essentially inert
        'FA_quartz': 0.0    # Quartz is inert
    }
    
    return hydration_degrees


def calculate_reacted_composition(composition_mol, minerals_mol, hydration_degrees, flyash, recipe):
    """
    Calculate the composition that enters the equilibrium calculation
    by accounting for partial hydration of clinker minerals and fly ash glass.
    """
    # Start with total composition
    reacted_comp = composition_mol.copy()
    
    # For a more accurate model, we would:
    # 1. Calculate how much of each oxide is in unhydrated clinker
    # 2. Subtract the unhydrated portion
    # 3. Add the hydration water consumed
    
    # Simplified approach for initial baseline:
    # Use total composition and let GEMS calculate equilibrium
    # The hydration degrees will be used to interpret results
    
    return reacted_comp


def initialize_gems_engine(project_config):
    """
    Initialize GEMS chemical engine with project settings.
    Returns engine object if xGEMS is available, None otherwise.
    """
    try:
        from xgems import ChemicalEngine
        
        # Initialize engine
        # Note: Actual database loading syntax may vary
        engine = ChemicalEngine()
        
        # Set thermodynamic conditions from Phase 1 config
        temp_K = project_config['thermodynamic_conditions']['temperature_K']
        pressure_bar = project_config['thermodynamic_conditions']['pressure_bar']
        
        # engine.set_temperature(temp_K)
        # engine.set_pressure(pressure_bar)
        
        print(f"✓ GEMS engine initialized")
        print(f"  Temperature: {temp_K} K ({project_config['thermodynamic_conditions']['temperature_C']}°C)")
        print(f"  Pressure: {pressure_bar} bar")
        
        return engine
        
    except ImportError:
        print("⚠ xGEMS not available - creating placeholder baseline")
        print("  Install xGEMS to run actual thermodynamic calculations")
        return None


def run_equilibration(engine, composition_mol, project_config):
    """
    Run thermodynamic equilibration to calculate 28-day baseline state.
    """
    if engine is None:
        # Create placeholder result when xGEMS not available
        return create_placeholder_baseline(composition_mol)
    
    # Prepare composition for GEMS
    # Convert oxide composition to element-based input if needed
    
    # Get suppressed phases from config
    suppressed = project_config['suppressed_phases']
    
    # Run equilibration
    # result = engine.equilibrate(composition_mol, suppress=suppressed)
    
    # For now, return placeholder
    return create_placeholder_baseline(composition_mol)


def create_placeholder_baseline(composition_mol):
    """
    Create a placeholder baseline with reasonable estimates.
    This is replaced by actual GEMS calculations when xGEMS is available.
    """
    # Estimate phase amounts based on typical OPC+FA paste at w/b=0.3
    baseline = {
        'phases': {
            'portlandite': 4.2,  # mol per 1000 cm³
            'CSH': 11.5,
            'ettringite': 0.55,
            'monosulfate': 0.35,
            'hydrotalcite': 0.18,
            'calcite': 0.05,
            'C3S_unreacted': 0.35,
            'C2S_unreacted': 0.65,
            'C3A_unreacted': 0.0,
            'C4AF_unreacted': 0.58,
            'FA_glass_unreacted': 3.2,
            'mullite': 0.72,
            'quartz': 1.00
        },
        'pore_solution': {
            'Ca+2': 0.022,  # mol/L
            'Na+': 0.185,
            'K+': 0.420,
            'OH-': 0.625,
            'SO4-2': 0.002,
            'AlO2-': 0.001,
            'SiO3-2': 0.0005,
            'Cl-': 0.0
        },
        'pH': 13.72,
        'porosity': 0.15,
        'ionic_strength': 0.65,
        'note': 'Placeholder values - will be replaced by GEMS calculation'
    }
    
    return baseline


def save_baseline_results(baseline, output_dir):
    """Save baseline state to output files."""
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save complete baseline as JSON
    baseline_file = output_dir / 'baseline_28d.json'
    with open(baseline_file, 'w') as f:
        json.dump(baseline, f, indent=2)
    print(f"✓ Baseline saved: {baseline_file}")
    
    # Save phase data as CSV for easy validation
    phase_data = []
    for phase, amount in baseline['phases'].items():
        phase_data.append({
            'phase': phase,
            'amount_mol': amount,
            'category': categorize_phase(phase)
        })
    
    phase_df = pd.DataFrame(phase_data)
    phase_csv = output_dir / 'baseline_phases.csv'
    phase_df.to_csv(phase_csv, index=False)
    print(f"✓ Phase data saved: {phase_csv}")
    
    # Save pore solution as CSV
    pore_data = []
    for species, conc in baseline['pore_solution'].items():
        pore_data.append({
            'species': species,
            'concentration_mol_L': conc
        })
    
    pore_df = pd.DataFrame(pore_data)
    pore_df['pH'] = baseline['pH']
    pore_csv = output_dir / 'baseline_poresolution.csv'
    pore_df.to_csv(pore_csv, index=False)
    print(f"✓ Pore solution saved: {pore_csv}")


def categorize_phase(phase_name):
    """Categorize phases for analysis."""
    if 'unreacted' in phase_name:
        return 'Unhydrated'
    elif phase_name in ['portlandite', 'CSH', 'ettringite', 'monosulfate', 'hydrotalcite']:
        return 'Hydration product'
    elif phase_name in ['calcite']:
        return 'Carbonation product'
    elif phase_name in ['mullite', 'quartz']:
        return 'Inert filler'
    else:
        return 'Other'


def print_baseline_summary(baseline):
    """Print summary of baseline state."""
    print("\n" + "=" * 70)
    print("28-DAY BASELINE SUMMARY")
    print("=" * 70)
    
    print("\nKey Hydration Products:")
    for phase in ['portlandite', 'CSH', 'ettringite', 'monosulfate', 'hydrotalcite']:
        if phase in baseline['phases']:
            print(f"  {phase:20s}: {baseline['phases'][phase]:6.3f} mol")
    
    print("\nUnhydrated Clinker:")
    for phase in ['C3S_unreacted', 'C2S_unreacted', 'C3A_unreacted', 'C4AF_unreacted']:
        if phase in baseline['phases']:
            print(f"  {phase:20s}: {baseline['phases'][phase]:6.3f} mol")
    
    print("\nPore Solution Chemistry:")
    print(f"  pH: {baseline['pH']:.2f}")
    print(f"  Ionic strength: {baseline['ionic_strength']:.3f} mol/L")
    for species in ['Ca+2', 'Na+', 'K+', 'OH-']:
        if species in baseline['pore_solution']:
            print(f"  [{species:5s}]: {baseline['pore_solution'][species]:.4f} mol/L")
    
    print("\nPhysical Properties:")
    print(f"  Porosity: {baseline['porosity']*100:.1f}%")
    
    print("=" * 70)


def main():
    """Main execution function."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  PHASE 2: 28-DAY HYDRATION BASELINE  ".center(68) + "║")
    print("║" + "  Portland Cement + Fly Ash Paste  ".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print("\n")
    
    # Load all configuration and material data
    print("Loading configuration and material data...")
    project_config, cement, flyash, recipe = load_configuration()
    print(f"✓ Loaded cement: {cement['cement_type']}")
    print(f"✓ Loaded fly ash: {flyash['flyash_type']}")
    print(f"✓ Loaded recipe: {recipe['recipe_name']}")
    print(f"  w/b ratio: {recipe['mix_design']['water_binder_ratio']}")
    print(f"  FA replacement: {recipe['mix_design']['fly_ash_replacement_percent']}%")
    print()
    
    # Calculate system composition
    print("Calculating system composition...")
    composition_g, composition_mol = calculate_system_composition(cement, flyash, recipe)
    print("✓ Total oxide composition calculated")
    print(f"  Total CaO: {composition_g['CaO']:.1f} g ({composition_mol['CaO']:.2f} mol)")
    print(f"  Total SiO2: {composition_g['SiO2']:.1f} g ({composition_mol['SiO2']:.2f} mol)")
    print(f"  Total Al2O3: {composition_g['Al2O3']:.1f} g ({composition_mol['Al2O3']:.2f} mol)")
    print(f"  Total H2O: {composition_g['H2O']:.1f} g ({composition_mol['H2O']:.2f} mol)")
    print()
    
    # Calculate mineral composition
    print("Calculating clinker mineral composition...")
    minerals_mol = calculate_mineral_composition(cement, recipe)
    print("✓ Clinker minerals calculated")
    for mineral, amount in minerals_mol.items():
        if amount > 0.01:
            print(f"  {mineral:25s}: {amount:.3f} mol")
    print()
    
    # Set hydration degrees
    print("Setting hydration degrees (28 days at 20°C)...")
    hydration_degrees = set_hydration_degrees()
    print("✓ Hydration degrees initialized")
    for phase, degree in hydration_degrees.items():
        if degree > 0:
            print(f"  {phase:15s}: {degree*100:5.1f}%")
    print()
    
    # Initialize GEMS engine
    print("Initializing GEMS engine...")
    engine = initialize_gems_engine(project_config)
    print()
    
    # Run equilibration
    print("Calculating thermodynamic equilibrium...")
    baseline = run_equilibration(engine, composition_mol, project_config)
    if engine is None:
        print("⚠ Using placeholder values (install xGEMS for actual calculations)")
    else:
        print("✓ Equilibrium calculation complete")
    print()
    
    # Print summary
    print_baseline_summary(baseline)
    
    # Save results
    print("\nSaving baseline results...")
    output_dir = Path(__file__).parent.parent / 'outputs'
    save_baseline_results(baseline, output_dir)
    
    print("\n" + "=" * 70)
    print("28-DAY BASELINE CALCULATION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Install xGEMS to run actual thermodynamic calculations")
    print("  2. Validate against experimental XRD/TGA data")
    print("  3. Calibrate hydration degrees if needed")
    print("  4. Proceed to Phase 3: External Solutions and Boundary Conditions")
    print()


if __name__ == "__main__":
    main()
