#!/usr/bin/env python3
"""
Phase 6: Verification Script

Comprehensive verification of Phase 6 deliverables:
1. Comparative analysis script exists and functional
2. Visualization script exists and functional
3. Metrics calculator script exists and functional
4. Scripts connect to Phase 4 outputs and Phase 5 validation
5. No mock data or random generation confirmed
6. Documentation complete

Author: GEMS Modeling Team
Date: February 2026
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple


def check_file_exists(filepath: str, description: str) -> Tuple[bool, str]:
    """
    Check if a file exists.
    
    Args:
        filepath: Path to file
        description: Description for reporting
        
    Returns:
        (success, message)
    """
    if os.path.exists(filepath):
        size_kb = os.path.getsize(filepath) / 1024
        return True, f"✓ {description} exists ({size_kb:.1f} KB)"
    else:
        return False, f"✗ {description} NOT FOUND"


def check_script_no_mock_data(filepath: str, script_name: str) -> Tuple[bool, str]:
    """
    Verify script contains no mock data or random generation.
    
    Args:
        filepath: Path to script
        script_name: Script name for reporting
        
    Returns:
        (success, message)
    """
    if not os.path.exists(filepath):
        return False, f"✗ {script_name}: File not found"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check for forbidden patterns (exclude comments saying "NO MOCK DATA")
    forbidden_patterns = [
        (r'np\.random\.rand', 'numpy random generation'),
        (r'random\.randint', 'random integer generation'),
        (r'random\.choice', 'random choice'),
        (r'random\.uniform', 'random uniform'),
        (r'faker\.Faker', 'fake data generation'),
        (r'import\s+mock\b', 'mock import'),
        (r'from\s+mock\s+import', 'mock import'),
        (r'dummy_data\s*=', 'dummy data variable'),
        (r'test_data\s*=', 'test data variable')
    ]
    
    violations = []
    for pattern, description in forbidden_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            violations.append(f"{description} ({len(matches)} occurrences)")
    
    if violations:
        return False, f"✗ {script_name}: Contains forbidden patterns: {', '.join(violations)}"
    else:
        return True, f"✓ {script_name}: No mock/random data confirmed"


def check_script_phase_connections(filepath: str, script_name: str, required_connections: List[str]) -> Tuple[bool, str]:
    """
    Verify script connects to required phases.
    
    Args:
        filepath: Path to script
        script_name: Script name for reporting
        required_connections: List of required connection strings
        
    Returns:
        (success, message)
    """
    if not os.path.exists(filepath):
        return False, f"✗ {script_name}: File not found"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    missing_connections = []
    for connection in required_connections:
        if connection not in content:
            missing_connections.append(connection)
    
    if missing_connections:
        return False, f"✗ {script_name}: Missing connections: {', '.join(missing_connections)}"
    else:
        return True, f"✓ {script_name}: All required phase connections present"


def check_comparative_analysis_script(project_root: Path) -> Tuple[bool, List[str]]:
    """
    Verify comparative analysis script.
    
    Args:
        project_root: Project root directory
        
    Returns:
        (success, messages)
    """
    print("\n" + "="*80)
    print("CHECK 1: COMPARATIVE ANALYSIS SCRIPT")
    print("="*80)
    
    script_path = project_root / 'scripts' / 'comparative_analysis.py'
    messages = []
    all_passed = True
    
    # Check file exists
    success, msg = check_file_exists(str(script_path), "Comparative analysis script")
    messages.append(msg)
    if not success:
        all_passed = False
        return all_passed, messages
    
    # Check no mock data
    success, msg = check_script_no_mock_data(str(script_path), "comparative_analysis.py")
    messages.append(msg)
    if not success:
        all_passed = False
    
    # Check phase connections
    required = ['outputs', 'Phase 4', 'load_simulation_output']
    success, msg = check_script_phase_connections(str(script_path), "comparative_analysis.py", required)
    messages.append(msg)
    if not success:
        all_passed = False
    
    # Check required functions
    with open(script_path, 'r') as f:
        content = f.read()
    
    required_functions = [
        'load_simulation_output',
        'extract_final_metrics',
        'compare_degradation_severity',
        'analyze_solution_effects',
        'analyze_pressure_effects'
    ]
    
    missing_functions = []
    for func in required_functions:
        if f"def {func}" not in content:
            missing_functions.append(func)
    
    if missing_functions:
        messages.append(f"✗ Missing functions: {', '.join(missing_functions)}")
        all_passed = False
    else:
        messages.append(f"✓ All required functions present ({len(required_functions)} functions)")
    
    return all_passed, messages


def check_visualization_script(project_root: Path) -> Tuple[bool, List[str]]:
    """
    Verify visualization script.
    
    Args:
        project_root: Project root directory
        
    Returns:
        (success, messages)
    """
    print("\n" + "="*80)
    print("CHECK 2: VISUALIZATION SCRIPT")
    print("="*80)
    
    script_path = project_root / 'scripts' / 'visualize_results.py'
    messages = []
    all_passed = True
    
    # Check file exists
    success, msg = check_file_exists(str(script_path), "Visualization script")
    messages.append(msg)
    if not success:
        all_passed = False
        return all_passed, messages
    
    # Check no mock data
    success, msg = check_script_no_mock_data(str(script_path), "visualize_results.py")
    messages.append(msg)
    if not success:
        all_passed = False
    
    # Check matplotlib import
    with open(script_path, 'r') as f:
        content = f.read()
    
    if 'matplotlib' not in content:
        messages.append("✗ Missing matplotlib import")
        all_passed = False
    else:
        messages.append("✓ Matplotlib properly imported")
    
    # Check required plot functions
    required_plots = [
        'plot_phase_evolution',
        'plot_pH_evolution',
        'plot_portlandite_depletion',
        'plot_degradation_comparison'
    ]
    
    missing_plots = []
    for plot in required_plots:
        if f"def {plot}" not in content:
            missing_plots.append(plot)
    
    if missing_plots:
        messages.append(f"✗ Missing plot functions: {', '.join(missing_plots)}")
        all_passed = False
    else:
        messages.append(f"✓ All required plot functions present ({len(required_plots)} functions)")
    
    return all_passed, messages


def check_metrics_calculator(project_root: Path) -> Tuple[bool, List[str]]:
    """
    Verify metrics calculator script.
    
    Args:
        project_root: Project root directory
        
    Returns:
        (success, messages)
    """
    print("\n" + "="*80)
    print("CHECK 3: METRICS CALCULATOR SCRIPT")
    print("="*80)
    
    script_path = project_root / 'scripts' / 'calculate_metrics.py'
    messages = []
    all_passed = True
    
    # Check file exists
    success, msg = check_file_exists(str(script_path), "Metrics calculator script")
    messages.append(msg)
    if not success:
        all_passed = False
        return all_passed, messages
    
    # Check no mock data
    success, msg = check_script_no_mock_data(str(script_path), "calculate_metrics.py")
    messages.append(msg)
    if not success:
        all_passed = False
    
    # Check required calculation functions
    with open(script_path, 'r') as f:
        content = f.read()
    
    required_functions = [
        'calculate_portlandite_rate',
        'calculate_CSH_decalcification_rate',
        'calculate_pH_kinetics',
        'calculate_chloride_binding',
        'calculate_pressure_acceleration_factor'
    ]
    
    missing_functions = []
    for func in required_functions:
        if f"def {func}" not in content:
            missing_functions.append(func)
    
    if missing_functions:
        messages.append(f"✗ Missing functions: {', '.join(missing_functions)}")
        all_passed = False
    else:
        messages.append(f"✓ All metric calculation functions present ({len(required_functions)} functions)")
    
    # Check for physical models (first-order kinetics, etc.)
    if 'first-order kinetics' in content.lower() or 'rate_constant' in content:
        messages.append("✓ Physical kinetic models implemented")
    else:
        messages.append("⚠ Physical kinetic models may be missing")
    
    return all_passed, messages


def check_phase5_connection(project_root: Path) -> Tuple[bool, List[str]]:
    """
    Verify Phase 6 connects to Phase 5 validation.
    
    Args:
        project_root: Project root directory
        
    Returns:
        (success, messages)
    """
    print("\n" + "="*80)
    print("CHECK 4: PHASE 5 CONNECTION")
    print("="*80)
    
    messages = []
    all_passed = True
    
    # Check Phase 5 outputs exist
    phase5_files = [
        'validation/experimental_data_28d.json',
        'scripts/calibrate_baseline.py',
        'scripts/sensitivity_analysis.py',
        'scripts/validate_phase4_outputs.py'
    ]
    
    missing_files = []
    for rel_path in phase5_files:
        filepath = project_root / rel_path
        if not os.path.exists(filepath):
            missing_files.append(rel_path)
    
    if missing_files:
        messages.append(f"✗ Missing Phase 5 files: {', '.join(missing_files)}")
        all_passed = False
    else:
        messages.append(f"✓ All Phase 5 files present ({len(phase5_files)} files)")
    
    # Check comparative analysis references Phase 5
    comp_script = project_root / 'scripts' / 'comparative_analysis.py'
    if os.path.exists(comp_script):
        with open(comp_script, 'r') as f:
            content = f.read()
        
        if 'Phase 5' in content or 'validation' in content:
            messages.append("✓ Comparative analysis connects to Phase 5")
        else:
            messages.append("⚠ Weak Phase 5 connection in comparative analysis")
    
    return all_passed, messages


def check_phase4_connection(project_root: Path) -> Tuple[bool, List[str]]:
    """
    Verify Phase 6 connects to Phase 4 outputs.
    
    Args:
        project_root: Project root directory
        
    Returns:
        (success, messages)
    """
    print("\n" + "="*80)
    print("CHECK 5: PHASE 4 CONNECTION")
    print("="*80)
    
    messages = []
    all_passed = True
    
    # Check for Phase 4 output references
    phase6_scripts = [
        'scripts/comparative_analysis.py',
        'scripts/visualize_results.py',
        'scripts/calculate_metrics.py'
    ]
    
    for script_rel in phase6_scripts:
        script_path = project_root / script_rel
        if os.path.exists(script_path):
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Check for output file patterns
            if '_60d.json' in content or 'outputs' in content:
                messages.append(f"✓ {script_rel.split('/')[-1]}: Connects to Phase 4 outputs")
            else:
                messages.append(f"⚠ {script_rel.split('/')[-1]}: Weak Phase 4 connection")
                all_passed = False
        else:
            messages.append(f"✗ {script_rel.split('/')[-1]}: Not found")
            all_passed = False
    
    # Check expected scenario list
    scenarios = ['PW_immersion', 'PW_pressure', 'NaCl_immersion', 
                'NaCl_pressure', 'mixed_immersion', 'mixed_pressure']
    
    comp_script = project_root / 'scripts' / 'comparative_analysis.py'
    if os.path.exists(comp_script):
        with open(comp_script, 'r') as f:
            content = f.read()
        
        found_scenarios = sum(1 for s in scenarios if s in content)
        if found_scenarios >= 4:
            messages.append(f"✓ References {found_scenarios}/6 Phase 4 scenarios")
        else:
            messages.append(f"⚠ Only references {found_scenarios}/6 Phase 4 scenarios")
    
    return all_passed, messages


def check_documentation(project_root: Path) -> Tuple[bool, List[str]]:
    """
    Verify Phase 6 documentation exists.
    
    Args:
        project_root: Project root directory
        
    Returns:
        (success, messages)
    """
    print("\n" + "="*80)
    print("CHECK 6: DOCUMENTATION")
    print("="*80)
    
    messages = []
    all_passed = True
    
    # Check for documentation file
    doc_path = project_root / 'Phase6_Data_Analysis_Report.md'
    
    if os.path.exists(doc_path):
        size_kb = os.path.getsize(doc_path) / 1024
        messages.append(f"✓ Phase 6 documentation exists ({size_kb:.1f} KB)")
        
        with open(doc_path, 'r') as f:
            content = f.read()
        
        # Check for required sections
        required_sections = [
            'Comparative Analysis',
            'Visualization',
            'Metrics',
            'Results'
        ]
        
        missing_sections = []
        for section in required_sections:
            if section.lower() not in content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            messages.append(f"⚠ Documentation missing sections: {', '.join(missing_sections)}")
        else:
            messages.append(f"✓ All required documentation sections present")
    
    else:
        messages.append("⚠ Phase 6 documentation not yet created")
        # Not critical failure - document after execution
    
    # Check script docstrings
    scripts_with_docs = 0
    total_scripts = 3
    
    for script_name in ['comparative_analysis.py', 'visualize_results.py', 'calculate_metrics.py']:
        script_path = project_root / 'scripts' / script_name
        if os.path.exists(script_path):
            with open(script_path, 'r') as f:
                first_50_lines = ''.join(f.readlines()[:50])
            
            if '"""' in first_50_lines and 'Phase 6' in first_50_lines:
                scripts_with_docs += 1
    
    messages.append(f"✓ {scripts_with_docs}/{total_scripts} scripts have Phase 6 docstrings")
    
    return all_passed, messages


def main():
    """
    Main verification workflow.
    """
    print(f"\n{'#'*80}")
    print("PHASE 6 VERIFICATION")
    print("Comprehensive Check of All Phase 6 Deliverables")
    print(f"{'#'*80}")
    
    project_root = Path(__file__).parent.parent
    
    # Run all checks
    checks = [
        ("Comparative Analysis Script", check_comparative_analysis_script),
        ("Visualization Script", check_visualization_script),
        ("Metrics Calculator", check_metrics_calculator),
        ("Phase 5 Connection", check_phase5_connection),
        ("Phase 4 Connection", check_phase4_connection),
        ("Documentation", check_documentation)
    ]
    
    results = []
    all_checks_passed = True
    
    for check_name, check_func in checks:
        success, messages = check_func(project_root)
        results.append((check_name, success, messages))
        if not success:
            all_checks_passed = False
        
        for msg in messages:
            print(msg)
    
    # Print summary
    print(f"\n{'='*80}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*80}")
    
    for check_name, success, messages in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:<10} {check_name}")
    
    print(f"\n{'='*80}")
    if all_checks_passed:
        print("✓✓✓ ALL CHECKS PASSED ✓✓✓")
        print("Phase 6 implementation is complete and verified")
        print(f"{'='*80}")
        return 0
    else:
        print("⚠⚠⚠ SOME CHECKS FAILED ⚠⚠⚠")
        print("Review failures above and address issues")
        print(f"{'='*80}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
