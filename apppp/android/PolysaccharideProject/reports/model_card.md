# Model Card — Polysaccharide Classification Model

**Version:** v20260318_1251
**Generated:** 2026-03-18 07:21 UTC
**Algorithm:** LogisticRegression
**Training Date:** 2026-03-18T12:51:51.630728

---

## 1. Intended Use

This model classifies polysaccharides into one of 6 functional categories
for **reference and educational purposes only**.

> [!IMPORTANT]
> This model is **NOT** a diagnostic device. It is a decision-support
> reference tool. It must NOT be used to make clinical decisions without
> independent medical expert review.

**Intended users:** Clinical researchers and pharmacists seeking quick reference
on polysaccharide functional taxonomy.

**Out of scope:**
- Diagnostic device or clinical diagnostic tool
- Therapeutic dosing recommendations
- Patient-specific clinical decisions
- Replacement for laboratory analysis or clinical expert judgment

---

## 2. Clinical Validity Status

| Item | Value |
|------|-------|
| **clinical_model_valid** | `True` |
| **Reason** | All acceptance criteria met. Safety Mode (KB-first) ML predictions enabled. |
| **Clinician-facing mode (KB-first)** | ML predictions ENABLED (all acceptance criteria met) |

---

## 3. Training Data Sources

| Source | Type | License |
|--------|------|---------|
| Expert-curated literature (30 polysaccharides × 20 augmented rows) | Real (literature-derived) | CC BY 4.0 |
| PubChem Compound API | Real molecular properties | Public Domain (US Gov) |
| ChEMBL Molecule API | Real molecular/therapeutic data | CC BY-SA 3.0 |
| PubChem BioAssay (expert-curated subset) | Real + expert-labeled | Public Domain + CC BY 4.0 |
| GlyConnect Glycan API | Real glycan structures | CC BY 4.0 |
| UniProt Glycan-related proteins | Real protein data | CC BY 4.0 |
| GlyCosmos Glycan Registry | Real glycan registry | CC BY 4.0 |

**Synthetic data:** None used in clinical model.
All synthetic datasets are stored separately in:
`datasets/raw/Polysaccharide_Datasets_Synthetic_DemoOnly/`

**Training set:** 430 samples
**Validation set:** 92 samples
**Test set:** 62 samples

---

## 4. Evaluation Results

| Metric | Value |
|--------|-------|
| Test Accuracy | 0.9677 |
| Test Macro-F1 | 0.9779 |
| Test Weighted-F1 | 0.9679 |
| Worst-class Recall | 0.9091 (Algal) |
| Macro-F1 Bootstrap 95% CI | [0.9387, 1.0] |
| External Validation Macro-F1 | 0.9737 |
| External Val Gap | 0.0042 |

### Acceptance Criteria Results

| Criterion | Required | Achieved | Passed |
|-----------|----------|----------|--------|
| macro_f1 >= 0.85 | (threshold) | 0.9779 | ✅ |
| worst_class_recall >= 0.80 | (threshold) | 0.9091 | ✅ |
| external_val_gap <= 0.05 | (threshold) | 0.0042 | ✅ |


### Top-5 Feature Importances

| Feature | Importance |
|---------|-----------|


---

## 5. Known Failure Modes

| Failure Mode | Description | Risk Level |
|---|---|---|
| Structural/Storage confusion | Structural polysaccharides (cellulose, chitin) can be confused with Storage (starch) when branching/linkage features are missing | Medium |
| Sparse input features | If <4 features are provided, model defaults to majority class | High |
| Unseen polysaccharide types | Model trained on 30 polysaccharide types; novel compounds may be misclassified | High |
| Out-of-distribution (OOD) | API-sourced unlabeled rows used for mapping may not generalize | Medium |

---

## 6. Confidence Threshold Policy

**Threshold:** `0.75`

- If `confidence < 0.75` → prediction NOT shown; fallback to Knowledge Base
- In **Clinician-facing mode (KB-first)** + `clinical_model_valid=false` → ALL predictions suppressed
- In **Demo Mode** → predictions shown when `confidence >= 0.75` with explicit "Demo Only" label

---

## 7. Versioning + Update Policy

- Version format: `vYYYYMMDD_HHMM`
- Current version: `v20260318_1251`
- Retrain when: new real labeled data available, or any acceptance criterion drops below threshold
- Distribution: model artifacts stored in `models/clinical/`; assets copied to `app/src/main/assets/`
- `model_manifest.json` is the single source of truth for deployment gate

---

## 8. Disclaimer

> This model card is generated automatically by the Polysaccharide Clinical Pipeline.
> It reflects the state of the model at training time.
> The model has **NOT** been reviewed by or approved by any regulatory body.
> It has **NOT** undergone clinical trials or prospective clinical validation.
> **Use for educational and research reference only.**
