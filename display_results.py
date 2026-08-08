#!/usr/bin/env python3
"""
Screening Results Display Tool
Shows screening results in JSON format for debugging
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Sample screening result
def get_sample_results() -> Dict[str, Any]:
    """Generate sample screening results"""
    return {
        "timestamp": datetime.now().isoformat(),
        "screening_session": "debug_session_001",
        "totalEvaluated": 15,
        "filteredOut": 8,
        "recommendations": [
            {
                "rank": 1,
                "materialId": "mat_001",
                "name": "Polylactic Acid (PLA)",
                "score": 94.5,
                "confidence": 0.92,
                "matchedRequirements": {
                    "mechanical": {
                        "required": True,
                        "passed": True,
                        "score": 85,
                        "constraint": "Tensile strength 50-60 MPa",
                        "actual_value": 55
                    },
                    "barrier": {
                        "required": True,
                        "passed": True,
                        "score": 78,
                        "constraint": "Oxygen transmission rate < 10 cm³/m²/day",
                        "actual_value": 8.5
                    },
                    "processing": {
                        "required": True,
                        "passed": True,
                        "score": 90,
                        "constraint": "Processing temperature < 250°C",
                        "actual_value": 200
                    },
                    "cost": {
                        "required": True,
                        "passed": True,
                        "score": 72,
                        "constraint": "Cost < $3/kg",
                        "actual_value": 2.80
                    }
                },
                "factorContributions": [
                    {"factor": "mechanical_strength", "weight": 0.35, "contribution": 29.75},
                    {"factor": "sustainability", "weight": 0.25, "contribution": 21.2},
                    {"factor": "processing_ease", "weight": 0.20, "contribution": 18.0},
                    {"factor": "cost", "weight": 0.20, "contribution": 14.4}
                ],
                "limitingFactors": ["cost", "thermal_stability"],
                "summary": "Best overall match for biodegradable applications"
            },
            {
                "rank": 2,
                "materialId": "mat_003",
                "name": "Polyhydroxyalkanoates (PHA)",
                "score": 88.2,
                "confidence": 0.85,
                "matchedRequirements": {
                    "mechanical": {
                        "required": True,
                        "passed": True,
                        "score": 72,
                        "constraint": "Tensile strength 50-60 MPa",
                        "actual_value": 52
                    },
                    "barrier": {
                        "required": True,
                        "passed": True,
                        "score": 68,
                        "constraint": "Oxygen transmission rate < 10 cm³/m²/day",
                        "actual_value": 12.5
                    },
                    "sustainability": {
                        "required": True,
                        "passed": True,
                        "score": 96,
                        "constraint": "Biodegradable within 180 days",
                        "actual_value": 120
                    }
                },
                "factorContributions": [
                    {"factor": "sustainability", "weight": 0.25, "contribution": 24.0},
                    {"factor": "mechanical_strength", "weight": 0.35, "contribution": 25.2},
                    {"factor": "barrier_properties", "weight": 0.20, "contribution": 13.6}
                ],
                "limitingFactors": ["processing_cost", "barrier_properties"],
                "summary": "Excellent for eco-friendly applications with good performance"
            }
        ],
        "limitingConstraints": [
            {
                "reason": "Low mechanical strength (< 40 MPa)",
                "failureCount": 4,
                "materials_affected": ["mat_005", "mat_008", "mat_010", "mat_012"]
            },
            {
                "reason": "High processing temperature (> 250°C)",
                "failureCount": 3,
                "materials_affected": ["mat_002", "mat_007", "mat_014"]
            },
            {
                "reason": "Cost exceeds budget (> $5/kg)",
                "failureCount": 1,
                "materials_affected": ["mat_015"]
            }
        ],
        "screening_criteria": {
            "mechanical": {"weight": 0.35, "requirement": "50-60 MPa tensile strength"},
            "barrier": {"weight": 0.25, "requirement": "< 10 cm³/m²/day oxygen transmission"},
            "sustainability": {"weight": 0.20, "requirement": "Biodegradable within 200 days"},
            "cost": {"weight": 0.20, "requirement": "< $3/kg"}
        },
        "summary_stats": {
            "pass_rate": "46.7%",
            "avg_score_passed": 91.35,
            "best_score": 94.5,
            "worst_score": 45.2
        }
    }


def display_results(results: Dict[str, Any], format: str = "pretty") -> None:
    """Display results in specified format"""
    
    if format == "pretty":
        print("\n" + "="*80)
        print("SCREENING RESULTS - DETAILED VIEW")
        print("="*80)
        
        print(f"\nTimestamp: {results.get('timestamp', 'N/A')}")
        print(f"Session: {results.get('screening_session', 'N/A')}")
        print(f"\nStatistics:")
        print(f"  Total Evaluated: {results['totalEvaluated']}")
        print(f"  Filtered Out: {results['filteredOut']}")
        print(f"  Recommendations: {len(results['recommendations'])}")
        print(f"  Pass Rate: {results['summary_stats']['pass_rate']}")
        
        print(f"\nTop Recommendations:")
        for rec in results['recommendations'][:3]:
            print(f"\n  [{rec['rank']}] {rec['name']}")
            print(f"      Score: {rec['score']}/100 | Confidence: {rec['confidence']*100:.0f}%")
            print(f"      Summary: {rec['summary']}")
            
        print(f"\nLimiting Constraints:")
        for constraint in results['limitingConstraints'][:3]:
            print(f"  • {constraint['reason']} ({constraint['failureCount']} materials)")
        
        print("\n" + "="*80)
        
    elif format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    elif format == "compact":
        print(json.dumps(results))


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Display screening results")
    parser.add_argument(
        "--format",
        choices=["pretty", "json", "compact"],
        default="pretty",
        help="Output format"
    )
    parser.add_argument(
        "--file",
        help="Load results from JSON file instead of sample"
    )
    
    args = parser.parse_args()
    
    if args.file:
        print(f"Loading results from {args.file}...")
        try:
            with open(args.file, 'r') as f:
                results = json.load(f)
        except Exception as e:
            print(f"Error loading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        results = get_sample_results()
    
    display_results(results, format=args.format)


if __name__ == "__main__":
    main()
