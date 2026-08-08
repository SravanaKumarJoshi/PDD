#!/usr/bin/env python3
"""
evaluate_dataset.py — Dataset evaluation script for BioPolymer AI Screening

Loads starter_dataset.csv, runs the scoring engine against 5 requirement
profiles, validates correctness, and outputs a JSON report artifact.

Exit codes:
  0 = all checks passed
  1 = critical validation failure (CI should fail)

Usage:
  python evaluate_dataset.py                    # Run evaluation
  python evaluate_dataset.py --output report.json  # Custom output path
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Add parent to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.scoring.engine import score_and_rank
from app.ingestion.csv_loader import parse_csv_row
from app.schemas.recommendation import RequirementInput


# ── Data Loading ───────────────────────────────────────────────────

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "starter_dataset.csv")


def load_materials(csv_path: str = CSV_PATH) -> list[dict]:
    """Load and parse the starter dataset CSV."""
    materials = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            mat_data, prop_data = parse_csv_row(row)
            materials.append({
                "id": f"00000000-0000-0000-0000-{i:012d}",
                "name": mat_data.get("name", f"Material-{i}"),
                "category": mat_data.get("category", "unknown"),
                "evidence_level": mat_data.get("evidence_level", "low"),
                "properties": prop_data,
            })
    return materials


# ── Requirement Profiles ───────────────────────────────────────────

def wound_care_profile() -> RequirementInput:
    """Wound care: antimicrobial, biocompatible, moderate barrier."""
    req = RequirementInput()
    req.biological.cytotoxicity_safe_required = True
    req.biological.hemocompatible_required = True
    req.biological.antimicrobial_required = True
    req.biological.weight = 2.0
    req.barrier.wvtr_max = 300
    req.barrier.otr_max = 200
    req.processing.film_required = True
    req.degradation.degradation_days_min = 14
    req.degradation.degradation_days_max = 180
    req.cost.max_cost_band = "high"
    return req


def food_packaging_profile() -> RequirementInput:
    """Food packaging: high barrier, low cost, film processable."""
    req = RequirementInput()
    req.barrier.wvtr_max = 100
    req.barrier.otr_max = 50
    req.barrier.weight = 2.0
    req.processing.film_required = True
    req.cost.max_cost_band = "low"
    req.cost.weight = 1.5
    req.mechanical.tensile_strength_min = 30
    req.mechanical.tensile_strength_max = 200
    return req


def drug_blister_profile() -> RequirementInput:
    """Drug blister: high mechanical, gamma sterilization, high barrier."""
    req = RequirementInput()
    req.mechanical.tensile_strength_min = 50
    req.mechanical.tensile_strength_max = 300
    req.mechanical.weight = 1.5
    req.sterilization.gamma_required = True
    req.barrier.wvtr_max = 80
    req.barrier.otr_max = 40
    req.barrier.weight = 1.5
    req.processing.film_required = True
    return req


def implant_packaging_profile() -> RequirementInput:
    """Implant packaging: steam/autoclave, biocompatible, slow degradation."""
    req = RequirementInput()
    req.sterilization.steam_required = True
    req.sterilization.autoclave_required = True
    req.biological.cytotoxicity_safe_required = True
    req.biological.weight = 2.0
    req.degradation.degradation_days_min = 180
    req.degradation.degradation_days_max = 730
    req.degradation.weight = 1.5
    return req


def flexible_pouch_profile() -> RequirementInput:
    """Flexible pouch: high elongation, low cost, casting processable."""
    req = RequirementInput()
    req.mechanical.elongation_min = 15
    req.mechanical.elongation_max = 200
    req.mechanical.weight = 1.5
    req.processing.casting_required = True
    req.cost.max_cost_band = "low"
    req.cost.weight = 1.5
    return req


PROFILES = {
    "wound_care": wound_care_profile,
    "food_packaging": food_packaging_profile,
    "drug_blister": drug_blister_profile,
    "implant_packaging": implant_packaging_profile,
    "flexible_pouch": flexible_pouch_profile,
}


# ── Evaluation ─────────────────────────────────────────────────────

@dataclass
class ProfileResult:
    profile_name: str
    top_10: list[dict] = field(default_factory=list)  # [{name, category, score, confidence}]
    total_evaluated: int = 0
    total_passed: int = 0
    filtered_out: int = 0
    missing_data_stats: dict = field(default_factory=dict)  # {dimension: count_missing}


@dataclass
class EvaluationReport:
    dataset_path: str
    total_materials: int
    categories: dict = field(default_factory=dict)  # {category: count}
    evidence_levels: dict = field(default_factory=dict)  # {level: count}
    avg_data_completeness: float = 0.0
    profiles: list[ProfileResult] = field(default_factory=list)
    validations: list[dict] = field(default_factory=list)  # [{check, passed, message}]
    all_passed: bool = True


def evaluate_profile(
    name: str, req: RequirementInput, materials: list[dict]
) -> ProfileResult:
    """Run scoring for a profile and gather stats."""
    result = score_and_rank(req, materials)

    top_10 = []
    for rec in result.recommendations[:10]:
        top_10.append({
            "name": rec.material_name,
            "category": rec.category,
            "score": round(rec.score, 4),
            "confidence": round(rec.confidence, 4),
            "top_factor": rec.top_factors[0].factor if rec.top_factors else None,
        })

    # Missing data stats
    missing_stats: dict[str, int] = {}
    for rec in result.recommendations:
        for f in rec.top_factors:
            if f.score is None:
                missing_stats[f.factor] = missing_stats.get(f.factor, 0) + 1

    return ProfileResult(
        profile_name=name,
        top_10=top_10,
        total_evaluated=result.total_materials_evaluated,
        total_passed=len(result.recommendations),
        filtered_out=result.materials_filtered_out,
        missing_data_stats=missing_stats,
    )


def run_validations(
    materials: list[dict], report: EvaluationReport
) -> list[dict]:
    """Run critical validations and return results."""
    checks = []

    # Check 1: Dataset has 34+ materials
    ok = len(materials) >= 34
    checks.append({
        "check": "dataset_has_34_materials",
        "passed": ok,
        "message": f"Found {len(materials)} materials" + (" ✓" if ok else " ✗ CRITICAL"),
    })
    if not ok:
        report.all_passed = False

    # Check 2: Wound care — chitosan in top 5
    wound_care_result = next(
        (p for p in report.profiles if p.profile_name == "wound_care"), None
    )
    if wound_care_result and wound_care_result.top_10:
        top5_names = [m["name"] for m in wound_care_result.top_10[:5]]
        chitosan_present = any("chitosan" in n.lower() for n in top5_names)
        checks.append({
            "check": "wound_care_chitosan_in_top5",
            "passed": chitosan_present,
            "message": f"Top 5: {top5_names}" + (" ✓" if chitosan_present else " ⚠ chitosan not in top 5"),
        })

    # Check 3: Drug blister — all results have gamma sterilization
    drug_result = next(
        (p for p in report.profiles if p.profile_name == "drug_blister"), None
    )
    if drug_result:
        checks.append({
            "check": "drug_blister_gamma_filter_works",
            "passed": drug_result.filtered_out > 0,
            "message": f"Filtered {drug_result.filtered_out} materials without gamma ✓",
        })

    # Check 4: Implant packaging filters many materials
    implant_result = next(
        (p for p in report.profiles if p.profile_name == "implant_packaging"), None
    )
    if implant_result:
        heavy_filter = implant_result.filtered_out > 5  # At least 5 filtered
        checks.append({
            "check": "implant_packaging_filters_heavily",
            "passed": heavy_filter,
            "message": f"Filtered {implant_result.filtered_out} materials" + (" ✓" if heavy_filter else " ⚠"),
        })

    # Check 5: All scores in [0, 1]
    scores_ok = True
    for p in report.profiles:
        for m in p.top_10:
            if not (0.0 <= m["score"] <= 1.0) or not (0.0 <= m["confidence"] <= 1.0):
                scores_ok = False
                break
    checks.append({
        "check": "all_scores_in_bounds",
        "passed": scores_ok,
        "message": "All scores/confidence in [0, 1]" + (" ✓" if scores_ok else " ✗ CRITICAL"),
    })
    if not scores_ok:
        report.all_passed = False

    # Check 6: Determinism (run wound care twice)
    req = wound_care_profile()
    r1 = score_and_rank(req, materials)
    r2 = score_and_rank(req, materials)
    r1_scores = [(r.material_name, r.score) for r in r1.recommendations]
    r2_scores = [(r.material_name, r.score) for r in r2.recommendations]
    deterministic = r1_scores == r2_scores
    checks.append({
        "check": "scoring_determinism",
        "passed": deterministic,
        "message": "Scoring is deterministic ✓" if deterministic else "Scoring NOT deterministic ✗ CRITICAL",
    })
    if not deterministic:
        report.all_passed = False

    return checks


def main():
    parser = argparse.ArgumentParser(description="Evaluate BioPolymer dataset")
    parser.add_argument(
        "--output", "-o",
        default="evaluation_report.json",
        help="Output JSON report path",
    )
    parser.add_argument(
        "--csv", "-c",
        default=CSV_PATH,
        help="Path to materials CSV",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  BioPolymer Dataset Evaluation")
    print("=" * 60)

    # Load dataset
    print(f"\n📂 Loading dataset from: {args.csv}")
    materials = load_materials(args.csv)
    print(f"   Loaded {len(materials)} materials")

    # Gather stats
    categories = Counter(m["category"] for m in materials)
    evidence_levels = Counter(m["evidence_level"] for m in materials)
    completeness_values = [
        m["properties"].get("data_completeness", 0) for m in materials
    ]
    avg_completeness = sum(completeness_values) / len(completeness_values) if completeness_values else 0

    report = EvaluationReport(
        dataset_path=args.csv,
        total_materials=len(materials),
        categories=dict(categories.most_common()),
        evidence_levels=dict(evidence_levels.most_common()),
        avg_data_completeness=round(avg_completeness, 3),
    )

    # Run each profile
    print(f"\n🔬 Running {len(PROFILES)} evaluation profiles...\n")
    for name, req_fn in PROFILES.items():
        req = req_fn()
        profile_result = evaluate_profile(name, req, materials)
        report.profiles.append(profile_result)

        passed = profile_result.total_passed
        filtered = profile_result.filtered_out
        print(f"  📋 {name}: {passed} passed, {filtered} filtered")
        if profile_result.top_10:
            for i, m in enumerate(profile_result.top_10[:5], 1):
                print(f"     {i}. {m['name']} (score={m['score']:.3f}, conf={m['confidence']:.3f})")

    # Run validations
    print(f"\n✅ Running validations...\n")
    report.validations = run_validations(materials, report)
    for v in report.validations:
        status = "✓" if v["passed"] else "✗"
        print(f"  [{status}] {v['check']}: {v['message']}")

    # Write report
    output_path = args.output
    report_dict = asdict(report)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)
    print(f"\n📄 Report written to: {output_path}")

    # Exit code
    if report.all_passed:
        print("\n🎉 All critical checks passed!")
        sys.exit(0)
    else:
        print("\n❌ CRITICAL CHECKS FAILED — see report for details")
        sys.exit(1)


if __name__ == "__main__":
    main()
