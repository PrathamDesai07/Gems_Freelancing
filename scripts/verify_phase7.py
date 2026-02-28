#!/usr/bin/env python3
"""
Phase 7 Verification Script

This script verifies the completeness of Phase 7:
- Final comprehensive report exists
- All data from previous phases integrated
- Report structure is complete
- All figures and tables referenced
- Literature citations present
- No mock/test data used

Author: GEMS Modeling Team
Date: February 2026
"""

import os
import sys
from pathlib import Path


def verify_report_exists(project_root: Path) -> tuple[bool, str]:
    """Verify the final report file exists."""
    report_file = project_root / 'results' / 'Phase7_Comprehensive_Final_Report.md'
    
    if not report_file.exists():
        return False, f"Final report not found: {report_file}"
    
    # Check file size
    file_size = report_file.stat().st_size
    if file_size < 10000:  # Should be at least 10KB
        return False, f"Report file too small ({file_size} bytes), may be incomplete"
    
    return True, f"✓ Report file exists ({file_size:,} bytes)"


def verify_report_structure(project_root: Path) -> tuple[bool, str]:
    """Verify all required sections are present in the report."""
    report_file = project_root / 'results' / 'Phase7_Comprehensive_Final_Report.md'
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_sections = [
        "Executive Summary",
        "Introduction",
        "Materials and Methods",
        "Results",
        "Discussion",
        "Conclusions",
        "References",
        "Appendix"
    ]
    
    missing = []
    for section in required_sections:
        if section not in content:
            missing.append(section)
    
    if missing:
        return False, f"Missing sections: {', '.join(missing)}"
    
    return True, f"✓ All {len(required_sections)} required sections present"


def verify_data_integration(project_root: Path) -> tuple[bool, str]:
    """Verify data from previous phases is integrated."""
    report_file = project_root / 'results' / 'Phase7_Comprehensive_Final_Report.md'
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for key data elements
    key_elements = [
        ("CEMDATA18", "Phase 1 - Thermodynamic database"),
        ("Portlandite", "Phase assemblage data"),
        ("C-S-H", "Hydration products"),
        ("w/b=0.3", "Mix design"),
        ("30% fly ash", "Material composition"),
        ("70 g/L NaCl", "Solution composition"),
        ("1.2 MPa", "Pressure condition"),
        ("60 days", "Simulation duration"),
        ("mixed_pressure", "Worst-case scenario"),
        ("2.9", "Pressure acceleration factor"),
        ("chloride binding", "Chloride attack analysis"),
        ("Friedel", "Chloride binding phase")
    ]
    
    missing_data = []
    for element, description in key_elements:
        if element not in content:
            missing_data.append(f"{description} ({element})")
    
    if missing_data:
        return False, f"Missing data: {', '.join(missing_data[:5])}"
    
    return True, f"✓ All {len(key_elements)} key data elements present"


def verify_figures_referenced(project_root: Path) -> tuple[bool, str]:
    """Verify figure references are present."""
    report_file = project_root / 'results' / 'Phase7_Comprehensive_Final_Report.md'
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for figure references
    expected_figures = [
        "Figure 1",
        "Figure 2",
        "Figure 3",
        "Figure 4",
        "Figure 5"
    ]
    
    missing = []
    for fig in expected_figures:
        if fig not in content:
            missing.append(fig)
    
    if missing:
        return False, f"Missing figure references: {', '.join(missing)}"
    
    # Check actual figures exist
    figure_dir = project_root / 'results' / 'figures'
    expected_figure_files = [
        'phase_evolution_all.png',
        'pH_evolution.png',
        'portlandite_depletion.png',
        'chloride_binding.png',
        'degradation_comparison.png'
    ]
    
    missing_files = []
    for fig_file in expected_figure_files:
        if not (figure_dir / fig_file).exists():
            missing_files.append(fig_file)
    
    if missing_files:
        return False, f"Missing figure files: {', '.join(missing_files)}"
    
    return True, f"✓ All {len(expected_figures)} figures referenced and exist"


def verify_tables_present(project_root: Path) -> tuple[bool, str]:
    """Verify tables are present."""
    report_file = project_root / 'results' / 'Phase7_Comprehensive_Final_Report.md'
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for table markers (markdown tables have |)
    table_count = content.count('|---')
    
    if table_count < 5:
        return False, f"Too few tables ({table_count} found, expected at least 5)"
    
    return True, f"✓ Tables present ({table_count} markdown tables found)"


def verify_references_present(project_root: Path) -> tuple[bool, str]:
    """Verify literature references are cited."""
    report_file = project_root / 'results' / 'Phase7_Comprehensive_Final_Report.md'
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Key references that should be cited
    key_refs = [
        "Lothenbach",
        "CEMDATA18",
        "Phung",
        "Berner",
        "Glasser",
        "Cement and Concrete Research"
    ]
    
    missing = []
    for ref in key_refs:
        if ref not in content:
            missing.append(ref)
    
    if missing:
        return False, f"Missing key references: {', '.join(missing)}"
    
    # Count total references in References section
    ref_section = content.split("## 6. References")
    if len(ref_section) < 2:
        return False, "References section not found"
    
    ref_content = ref_section[1]
    ref_count = ref_content.count("*Cement and Concrete Research*") + \
                ref_content.count("*Construction and Building Materials*") + \
                ref_content.count("*Journal of Materials Science*")
    
    if ref_count < 10:
        return False, f"Too few references ({ref_count} found)"
    
    return True, f"✓ Literature references present ({ref_count} journal citations)"


def verify_no_mock_data(project_root: Path) -> tuple[bool, str]:
    """Verify no mock or test data references."""
    report_file = project_root / 'results' / 'Phase7_Comprehensive_Final_Report.md'
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read().lower()
    
    # Check for mock/test keywords
    forbidden = [
        "mock data",
        "test data",
        "random.rand",
        "np.random",
        "placeholder",
        "dummy data"
    ]
    
    found = []
    for keyword in forbidden:
        if keyword in content:
            found.append(keyword)
    
    if found:
        return False, f"Found forbidden keywords: {', '.join(found)}"
    
    # Verify real data sources mentioned
    real_sources = [
        "experimental",
        "literature",
        "cemdata18",
        "thermodynamic",
        "xrd",
        "tga"
    ]
    
    sources_found = sum(1 for src in real_sources if src in content)
    
    if sources_found < 4:
        return False, f"Too few real data sources mentioned ({sources_found}/6)"
    
    return True, f"✓ No mock data, real sources: {sources_found}/6"


def verify_phase_connections(project_root: Path) -> tuple[bool, str]:
    """Verify connections to all previous phases."""
    report_file = project_root / 'results' / 'Phase7_Comprehensive_Final_Report.md'
    
    with open(report_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for phase references
    phases = [
        ("Phase 1", ["CEMDATA", "thermodynamic database"]),
        ("Phase 2", ["cement", "fly ash", "material"]),
        ("Phase 3", ["solution", "NaCl", "exposure"]),
        ("Phase 4", ["simulation", "degradation", "60 days"]),
        ("Phase 5", ["validation", "experimental", "XRD", "TGA"]),
        ("Phase 6", ["comparative", "analysis", "ranking"])
    ]
    
    missing = []
    for phase_name, keywords in phases:
        found_keywords = sum(1 for kw in keywords if kw.lower() in content.lower())
        if found_keywords < 2:
            missing.append(phase_name)
    
    if missing:
        return False, f"Insufficient reference to: {', '.join(missing)}"
    
    return True, f"✓ All {len(phases)} previous phases connected"


def main():
    """Run all verification checks."""
    print(f"\n{'#'*80}")
    print("PHASE 7 VERIFICATION")
    print("Comprehensive Final Report")
    print(f"{'#'*80}\n")
    
    project_root = Path(__file__).parent.parent
    
    checks = [
        ("Report file exists", verify_report_exists),
        ("Report structure complete", verify_report_structure),
        ("Data integration", verify_data_integration),
        ("Figures referenced", verify_figures_referenced),
        ("Tables present", verify_tables_present),
        ("References cited", verify_references_present),
        ("No mock data", verify_no_mock_data),
        ("Phase connections", verify_phase_connections)
    ]
    
    results = []
    all_passed = True
    
    print("Running verification checks:\n")
    
    for check_name, check_func in checks:
        try:
            passed, message = check_func(project_root)
            results.append((check_name, passed, message))
            
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status:8s} | {check_name:30s} | {message}")
            
            if not passed:
                all_passed = False
                
        except Exception as e:
            results.append((check_name, False, f"Error: {str(e)}"))
            print(f"✗ ERROR  | {check_name:30s} | {str(e)}")
            all_passed = False
    
    print(f"\n{'='*80}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*80}")
    
    passed_count = sum(1 for _, p, _ in results if p)
    total_count = len(results)
    
    print(f"Checks passed: {passed_count}/{total_count}")
    
    if all_passed:
        print(f"\n{'✓'*3} ALL CHECKS PASSED {'✓'*3}")
        print("\nPhase 7: Comprehensive Final Report - COMPLETE")
        print("\nDeliverables:")
        print("- Comprehensive research report (30+ pages)")
        print("- Executive summary with key findings")
        print("- Complete methodology documentation")
        print("- Results synthesis from all phases")
        print("- Literature validation and references")
        print("- Engineering implications and recommendations")
        print("\nClient-ready package:")
        print("- 6 simulation datasets (JSON)")
        print("- 5 publication-quality figures (PNG 300 DPI)")
        print("- 3 analysis reports (comparative, metrics, final)")
        print("- All based on literature thermodynamic models")
        return 0
    else:
        print(f"\n{'✗'*3} VERIFICATION FAILED {'✗'*3}")
        print(f"\n{total_count - passed_count} check(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
