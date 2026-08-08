# Red Flag Closure Evidence

This document maps all 6 Red Flags to the specific files, configurations, and verification metrics that prove they have been successfully resolved in the current clinical pipeline.

| Red Flag | Resolution Description | Evidence Link / File Path | Status |
|---|---|---|---|
| **RF1: Synthetic-only data** | Pipeline downloads and exclusively uses real data from 5 APIs/Curated sources. Synthetic data is partitioned to a DemoOnly folder. | `scripts/download_real_datasets.py` <br> `datasets/raw/Polysaccharide_Datasets_All/` | ✅ VERIFIED |
| **RF2: Sparse Unknown-heavy merge** | Replaced the 73-column merging strategy with a dense 20-feature normalized schema. Rows missing >40% of required clinical features are proactively dropped. | `data_schema.md` <br> `scripts/preprocess_clinical.py` (line 424 `MISSINGNESS_THRESHOLD` check) | ✅ VERIFIED |
| **RF3: Data leakage risk** | `BLOCKED_FEATURES` array enforced (names, IDs, synonyms). A leakage audit dynamically tests if 3 probe models (DT, LR, RF) can predict the category from blocked features before accepting the dataset. | `scripts/preprocess_clinical.py` (lines 201 `run_leakage_audit`) <br> `datasets/metadata/data_quality_report.json` (`leakage_audit_passed: true`) | ✅ VERIFIED |
| **RF4: Structural vs Storage confusion** | Key discriminative features (`linkage_type`, `branching_category`, `crystallinity_category`, etc.) added. Final confusion matrix confirms 0 Structural/Storage cross-misclassifications. | `reports/clinical_test_results.json` (`rf4_structural_as_storage`: 0) | ✅ VERIFIED |
| **RF5: Sanity test mismatch** | Sanity UI tests now use actual held-out rows matched to the 20-feature schema from the test dataset rather than handcrafted non-representative dictionaries. | `scripts/test_clinical_model.py` <br> `reports/clinical_test_results.json` (`sanity_checks_accuracy`: 0.9333) | ✅ VERIFIED |
| **RF6: Android Safety Gaps & External Validation** | Acceptance Criteria established (F1 ≥ 0.85). Evaluated on an external proxy split (not a true independent prospective dataset). If failed, `clinical_model_valid` goes to false. Android layer disables predictions entirely if false, defaulting to a new Knowledge Base with 16 polysaccharides. | `app/src/main/java/com/biopolymer/screening/ml/ClinicalSafetyManager.kt` <br> `app_assets/polysaccharide_knowledge_base.json` (16 citations) | ✅ VERIFIED |

---

## Metric Verification Details

- **Leakage Audit Checks**: The baseline chance threshold was `0.2667`. Blocked features were stripped, resulting in 0 leaky columns passed to the ML layer, yielding a passed audit in the final preprocess stage.
- **RF5 Sanity Output**: Evaluated against 15 randomly chosen schema-matched test rows. Result: 14/15 correct (accuracy 93.33%).
- **RF6 External Gap**: Evaluated using the latest end-of-test-split batch. Measured `val_macro_f1` gap was `0.0042` (below the 0.05 threshold). Note: this is a proxy split, not a truly independent external validation set.

---

## Remaining Clinical-Use Gaps

While technical red flags are resolved, the following gaps persist before any clinical deployment is possible:
- **No prospective clinical study**: The model has only been evaluated retrospectively on dataset splits.
- **Unclear regulatory status**: The tool is unassessed by the FDA or equivalent agencies.
- **Unknown performance on real hospital/lab data**: Data is from chemical databases (PubChem/ChEMBL), which may not perfectly match messy hospital EHR or lab instrument outputs.
- **No bias/fairness assessment**: The model's performance equity across different molecular sources or edge cases is unquantified.
- **No cybersecurity/privacy assessment**: If patient data is ever involved, a full HIPAA/GDPR audit and penetration testing are required. Currently, the local audit log is designated as PHI-free, but system-level validation is absent.
