# Executive Summary for Clinicians & Auditors

**System:** Polysaccharide ML Pipeline and Clinical Application  
**Version:** v20260318_0959  
**Validation Status:** **Technical validation passed; NOT clinically validated; not a diagnostic device.**

---

## 1. Intended Use and Scope
This application acts as a digital educational and reference tool regarding the functional classifications of polysaccharides. 
It provides **decision support only; it is NOT a diagnostic device, does not recommend treatments or dosing, and requires human oversight.**

**Validation Scope:**
- Trained on 430 expert-curated and API-sourced (PubChem/ChEMBL) samples.
- Covers only 30 basic polysaccharide types across 6 high-level categories.
- Extreme risk of population mismatch if applied to novel clinical samples or complex clinical formulations not present in the training data.

**LIMITATION STATEMENT:** 
> This tool provides decision support only; it is **NOT** a diagnostic device, does not recommend treatments or dosing, and is severely limited by available training population size (n=430). All predictions must be correlated with clinical expertise or primary literature.
> **Human oversight is strictly required.** Not for diagnosis, treatment selection, or dosing.

## 2. Safety Mechanisms (Android Layer)
The application operates under a strict **Clinical Safety Manager** protocol:
- **Model Manifest Gating:** The mobile application reads the ML training manifest (`model_manifest.json`). If the model fails any acceptance criterion during training, ML predictions are strictly disabled fleet-wide in "Clinician-facing mode (KB-first)."
- **Knowledge Base Fallback:** If predictions are disabled, or if the model confidence is low, the app defaults to an onboard Evidence Knowledge Base containing strictly peer-reviewed, cited data on 16 common polysaccharides.
- **Confidence Thresholding:** ML predictions are only presented if confidence exceeds `0.75`.

## 3. Data Integrity & Validation (Pipeline Layer)
A major upgrade replaced previous proof-of-concept components with auditable pipelines:
1. **Real-World Provenance:** 100% of the training data driving Clinician-facing mode (KB-first) is derived from verifiable real-world registries (PubChem, ChEMBL, Curated Literature). Synthetic data is strictly barred from the clinical training branch.
2. **Dense Schema Enforcement:** Only inputs containing verified structural attributes are permitted. Sparse or incomplete molecular data (>40% missing features) is automatically rejected.
3. **Anti-Leakage Audit:** Every dataset must programmatically pass an Anti-Leakage test where statistical probe models attempt to predict out-of-bounds fields. If successful, the pipeline halts—meaning zero clinical labels can be accidentally inferred from dataset "names" or "IDs".
4. **Discriminative Capability:** Discriminative structural features properly eliminate prior confusions between `Storage` and `Structural` polysaccharides (0 misclassifications in final tests).

## 4. Final Evaluated Performance
The current clinical model meets and exceeds all mandated acceptance criteria:
- **Test Accuracy**: 98.39%
- **Test Macro-F1**: 98.74%
- **Worst-Class Recall**: 90.91% (Algal)
- **External Proxy Gap**: 0.42% variance between internal and proxy external splits.

### Final Conclusion
The ML prediction capability has passed **engineering safety gating** and is permitted for educational reference use inside the Safety Mode (KB-first). It provides categorization gated safely by a 75% confidence limit and backed by an onboard citation-heavy literature reference.
It is **NOT** approved for clinical decisions, is **NOT** clinically validated, and **MUST NOT** be relied upon for patient care.
