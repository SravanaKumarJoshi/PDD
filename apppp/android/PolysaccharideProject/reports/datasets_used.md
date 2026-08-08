              # Datasets Used Report
**Run Timestamp:** 2026-03-18T13:45:00Z
**Pipeline Stage:** Preprocessing + Training + Testing
**Git Commit:** not available

## Raw Dataset Inventory
| ID | Dataset Name | Source | API / Query | License | Retrieval Date | Local Path | Format | Size | Rows | Cols |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| real_01 | PubChem Polysaccharide Compounds | PubChem (NCBI) | keyword=polysaccharide | Public Domain | 2026-03-18 | D:\Sravan\PDD\apppp\android\PolysaccharideProject\datasets\raw\Polysaccharide_Datasets_All\realdata_01_pubchem_polysaccharides.csv | csv | 3.2 KB | 10 | 13 |
| real_02 | ChEMBL Glycan Molecules | ChEMBL (EBI) | pref_name__icontains=['polysaccharide'...] | CC BY-SA 3.0 | 2026-03-18 | D:\Sravan\PDD\apppp\android\PolysaccharideProject\datasets\raw\Polysaccharide_Datasets_All\realdata_02_chembl_glycan_molecules.csv | csv | 5.4 KB | 60 | 16 |
| real_05 | PubChem Expert-Curated | PubChem + Expert | CIDs: [16211032...] | CC BY 4.0 | 2026-03-18 | D:\Sravan\PDD\apppp\android\PolysaccharideProject\datasets\raw\Polysaccharide_Datasets_All\realdata_05_pubchem_polysaccharide_properties.csv | csv | 6.6 KB | 20 | 11 |

## Processed Lineage
- **Processed File:** `datasets/processed/master_clinical_dataset.csv`
- **SHA256:** `ba9ebebf6ebc369787d212c47c32aa21` (MD5 from manifest used as proxy)
- **Total Rows:** 615
- **Label Column:** `functional_category`
- **Missingness Threshold:** > 40% Required Features missing dropped.
- **Effective Feature List (Strict Order):**
  1. molecular_weight_kda
  2. degree_of_polymerization_log
  3. xcomplexity_norm
  4. hb_acceptors
  5. sulfation_present
  6. acetylation_present
  7. is_heteropolymer
  8. known_medical_use
  9. known_food_use
  10. biodegradable
  11. biocompatible
  12. monomer_type
  13. backbone_type
  14. linkage_type
  15. branching_category
  16. source_kingdom
  17. solubility_category
  18. charge_character
  19. crystallinity_category
  20. viscosity_category

## Leakage Audit Summary
- **Leakage Audit Passed:** ✅ YES
- **Threshold Value:** 0.2667 (Chance + 0.10)
- **Status:** PASS
- **Reason:** No blocked features (IDs, Names, SMILES) present in training dataset.
- **Full Report:** [data_quality_report.json](../datasets/metadata/data_quality_report.json)

## Split & Reproducibility
- **Random Seed:** 42
- **Split Strategy:** Stratified Shuffle Split
- **Dataset Hash (MD5):** `ba9ebebf6ebc369787d212c47c32aa21`
- **Reproducibility Status:** ✅ VERIFIED
- **Metric Mismatch:** < 1e-6 (Manifest vs Test Results vs Recompute Audit)

---
**Warning Section:** All datasets used are curated from public repositories. While PubChem and ChEMBL are reputable, clinical utility depends on the expert annotations in `realdata_05`. Model is for decision support only.
