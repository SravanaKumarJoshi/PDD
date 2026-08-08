# Polysaccharide Data Schema & Provenance

## Track Definitions
- **Track A (Chemistry Taxonomy):** DERIVED from chemical databases (PubChem, ChEMBL). Labels: Monomer Type, Linkage Family, Solubility Class.
- **Track B (Clinical):** REQUIRES gold-standard clinical labels. If not present, `clinical_model_valid` is set to `false`.

## Input Features (Dense Schema)
| Feature | Type | Source | Inclusion |
|---------|------|--------|-----------|
| mw_kda | Numeric | Chemical Specs | Required |
| source_origin | Categorical | Taxonomy | Required |
| monomer_unit | Categorical | PubChem/ChEMBL | Required |
| bond_type | Categorical | Structural Data | Required |

## Blocked Features (Leakage Prevention)
- names, IDs, synonyms
- free-text descriptions
- "expected_category"
- dataset_id
- researcher_notes
