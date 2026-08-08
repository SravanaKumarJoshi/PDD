# Model Card — BioPolymer AI Screening Platform

## Overview

This platform contains **two decision systems**:

1. **Recommendation Engine** — Rule-based scoring (production)
2. **Taxonomy Classifier** — TFLite neural network (experimental, gated)

---

## 1. Recommendation Engine (Rule-Based Scoring)

### Intended Use
Decision-support tool for screening natural polysaccharides as biomedical packaging materials. Ranks candidate materials against user-specified requirements across mechanical, barrier, degradation, biological, cost, and processing dimensions.

### How It Works
- **6-phase pipeline:** Hard constraint filtering → numeric range scoring → boolean/categorical scoring → weighted aggregation → confidence computation → explanation generation
- **Deterministic:** Same inputs always produce same outputs (verified across 100 runs)
- **Transparent:** Every recommendation includes per-factor contribution scores, concern flags, and tradeoff summaries

### Dataset
- **34 materials** across 14 polysaccharide families
- **37 properties** per material (mechanical, barrier, biological, sterilization, processing, cost)
- **DOI-backed** from 14 peer-reviewed publications
- **Evidence levels:** `low` (estimated/limited), `med` (2–5 sources), `high` (>5 consistent sources)

### Limitations

> **Critical:** Property values are screening-grade approximations, not certified specifications. Values are highly dependent on formulation, preparation method, MW, crosslinking conditions, and test methodology.

- **Small dataset:** 34 materials may not cover all commercially relevant biopolymers
- **Range estimates:** Min/max values represent literature ranges, not specific formulations
- **Missing test conditions:** Assumed standard conditions (23°C, 50% RH) unless noted
- **No blend optimization:** Materials scored independently; synergistic blends not modeled

### Evaluation

| Metric | Result | Method |
|--------|--------|--------|
| Determinism | ✅ 100/100 identical runs | `test_determinism_100_runs` |
| Score bounds | ✅ All in [0, 1] | `test_score_bounds` |
| Missing data handling | ✅ Partial credit (0.3) | `test_all_null_properties` |
| Wound care plausibility | ✅ Chitosan in top 5 | `evaluate_dataset.py` |
| Constraint enforcement | ✅ Non-gamma materials filtered | `test_hard_filters` |

### Risks
- **Over-reliance:** Users may treat screening results as final material specifications
- **Data staleness:** Properties may not reflect latest research or commercial formulations
- **Weight sensitivity:** Final ranking is sensitive to user-assigned dimension weights

---

## 2. Taxonomy Classifier (Experimental — TFLite)

### Intended Use
Classify polysaccharide compounds by category (e.g., Storage, Structural, GAG, Bacterial) from structural descriptors—intended for educational reference only.

### Model Details
- **Type:** Feed-forward neural network (Keras proxy trained from sklearn RandomForest)
- **Input features:** Molecular weight, solubility, bond type, source, monomer unit
- **Output:** Category probabilities (softmax over 6–8 classes)
- **Format:** TensorFlow Lite for Android deployment

### Clinical Safety Gating
- **`clinical_model_valid = false`** — predictions are disabled in Clinical mode
- **`ClinicalSafetyManager`** enforces confidence thresholds and mode-based gating
- Predictions displayed with disclaimer: *"Reference classification output (not clinical decision support)"*

### Limitations
- **Synthetic training data:** Taxonomy dataset generated from 8 template polysaccharides with Gaussian noise
- **Limited real validation:** No independent test set from measured experimental data
- **Not peer-reviewed:** Model and training pipeline have not undergone independent clinical validation

### Risks
- **False confidence:** Model may output high-confidence predictions for out-of-distribution inputs
- **Domain mismatch:** Structural descriptors do not capture formulation-dependent properties relevant to packaging
- **NOT a medical device:** Must not be used for clinical decisions

---

## Ethical Considerations

- **Biomedical context:** While used for packaging (not treatment), incorrect material selection could affect drug stability, sterilization effectiveness, or patient exposure
- **Transparency:** All recommendations include explanations, confidence scores, and evidence-level warnings
- **User agency:** The system recommends and explains — it does not prescribe

---

## Version

| Component | Version |
|-----------|---------|
| Scoring engine | `1.0.0` |
| Taxonomy classifier | Experimental (not versioned for clinical use) |
| Dataset | `starter_dataset.csv` (34 materials, 14 DOI sources) |
| Last updated | 2026-04-22 |
