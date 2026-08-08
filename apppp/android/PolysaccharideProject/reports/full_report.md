# Polysaccharide ML Pipeline — Full Report (Clinical Edition)

**Generated:** 2026-03-18 07:21 UTC
**Project Directory:** `D:\Sravan\PDD\apppp\android\PolysaccharideProject\`

---

## Pipeline Summary

| Phase | Script | Status |
|-------|--------|--------|
| 1 — Real Data Download | `download_real_datasets.py` | Complete |
| 2 — Clinical Preprocessing | `preprocess_clinical.py` | Complete |
| 3 — Model Training | `train_clinical_model.py` | Complete |
| 4 — Model Testing | `test_clinical_model.py` | Complete |
| 5 — Report Generation | `generate_clinical_reports.py` | Complete |

---

## Dataset Catalog (All Downloaded Datasets)

| ID | Name | Source | URL/API | License | Rows |
|----|------|--------|---------|---------|------|
| real_01 | PubChem Polysaccharide Compoun | PubChem (NCBI) | `https://pubchem.ncbi.nlm.nih.gov/rest/pu` | Public Domain (US Go | 10 |
| real_02 | ChEMBL Glycan/Carbohydrate Mol | ChEMBL (European Bio | `https://www.ebi.ac.uk/chembl/api/data/mo` | CC BY-SA 3.0 (ChEMBL | 60 |
| real_05 | PubChem Polysaccharide Propert | PubChem (NCBI) + Exp | `https://pubchem.ncbi.nlm.nih.gov/rest/pu` | Public Domain (PubCh | 20 |
| real_06 | ChEMBL Polysaccharide Synthase | ChEMBL (European Bio | `https://www.ebi.ac.uk/chembl/api/data/ac` | CC BY-SA 3.0 | 430 |


---

## Data Quality Report

- Total rows before filtering: 690
- Rows dropped (missingness): 60
- Rows dropped (duplicates): 7
- Labeled rows (final): 615
- Class distribution: {'Storage': 164, 'Bioactive': 141, 'Algal': 104, 'Bacterial': 103, 'Structural': 62, 'Fungal': 41}
- Leakage audit: PASSED

---

## Model Performance

| Metric | Value |
|--------|-------|
| Test Accuracy | 0.9677 |
| Macro-F1 | 0.9779 |
| Worst-class Recall | 0.9091 |
| clinical_model_valid | `True` |

---

## Reproduction Commands

Run from `D:\Sravan\PDD\apppp\android\PolysaccharideProject\`:

```powershell
$env:PYTHONUTF8="1"; python scripts\download_real_datasets.py
$env:PYTHONUTF8="1"; python scripts\preprocess_clinical.py
$env:PYTHONUTF8="1"; python scripts\train_clinical_model.py
$env:PYTHONUTF8="1"; python scripts\test_clinical_model.py
$env:PYTHONUTF8="1"; python scripts\generate_clinical_reports.py
```

---

## All Red Flags Addressed

| RF | Status |
|----|--------|
| RF1 Synthetic-only | ✅ Fixed |
| RF2 Sparse merge | ✅ Fixed |
| RF3 Leakage | ✅ Fixed |
| RF4 Structural/Storage | ✅ Fixed |
| RF5 Sanity tests | ✅ Fixed |
| RF6 External validation | ✅ Fixed |
