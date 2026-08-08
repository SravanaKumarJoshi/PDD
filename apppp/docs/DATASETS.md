# Datasets — BioPolymer AI Screening Platform

## Overview

The BioPolymer AI Screening Platform uses a curated starter dataset of **34 natural biopolymer materials** for its recommendation engine. This document describes the dataset structure, sources, and important scientific caveats.

> [!CAUTION]
> **Scientific Disclaimer**: The property values in the starter dataset are **approximate** and may be derived from
> a combination of published literature, manufacturer datasheets, and expert estimates. Property values are
> **highly dependent on formulation, preparation method, molecular weight, degree of substitution, crosslinking
> conditions, and test methodology**. The `evidence_level` field indicates the reliability of the reported data.
> These values should be treated as screening-grade guidance, not certified specifications.

---

## Starter Dataset (`backend/data/starter_dataset.csv`)

### Materials by Category

| Category | Count | Materials |
|----------|-------|-----------|
| `chitosan` | 4 | Chitosan (High MW), Chitosan (Low MW), Chitosan-PVA Blend, Chitin Nanowhisker |
| `alginate` | 2 | Sodium Alginate, Calcium Alginate |
| `cellulose` | 5 | Cellulose Nanocrystal (CNC), Cellulose Nanofiber (CNF), Bacterial Cellulose, Carboxymethyl Cellulose (CMC), Hydroxypropyl Methylcellulose (HPMC) |
| `starch` | 3 | Thermoplastic Starch (TPS), Starch Nanocrystal, Oxidized Starch |
| `pectin` | 2 | High-Methoxyl Pectin, Low-Methoxyl Pectin |
| `hyaluronic_acid` | 2 | Hyaluronic Acid (HA), Crosslinked HA (HA-BDDE) |
| `pullulan` | 2 | Pullulan, Pullulan-Chitosan Blend |
| `dextran` | 2 | Dextran, Dextran Methacrylate |
| `gellan` | 2 | Gellan Gum (High Acyl), Gellan Gum (Low Acyl) |
| `agar` | 2 | Agar, Agarose |
| `carrageenan` | 3 | Kappa-Carrageenan, Iota-Carrageenan, Lambda-Carrageenan |
| `guar` | 2 | Guar Gum, Hydroxypropyl Guar |
| `xanthan` | 2 | Xanthan Gum, Xanthan-Guar Synergistic Blend |
| `glucomannan` | 1 | Konjac Glucomannan |

---

## Column Definitions

### Material Identification

| Column | Type | Description |
|--------|------|-------------|
| `name` | text | Material display name (required) |
| `category` | text | Polysaccharide family (e.g., `chitosan`, `alginate`, `cellulose`) |
| `source` | text | Biological source (e.g., "Crustacean shells", "Brown algae") |
| `evidence_level` | enum | `low` / `med` / `high` — data confidence level |
| `notes` | text | Key considerations (MW, substitution degree, etc.) |
| `references` | text | Primary literature DOI or citation |

### Mechanical Properties

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `tensile_min` | float | MPa | Minimum tensile strength range |
| `tensile_max` | float | MPa | Maximum tensile strength range |
| `modulus_min` | float | GPa | Minimum elastic (Young's) modulus |
| `modulus_max` | float | GPa | Maximum elastic modulus |
| `elongation_min` | float | % | Minimum elongation at break |
| `elongation_max` | float | % | Maximum elongation at break |
| `puncture_resistance` | float | N | Puncture resistance (direct force) |

### Barrier Properties

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `wvtr` | float | g/m²/day | Water Vapor Transmission Rate (lower = better barrier) |
| `otr` | float | cc/m²/day | Oxygen Transmission Rate (lower = better barrier) |

### Solubility & Swelling

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `water_solubility` | bool | — | Soluble in water at ambient conditions |
| `swelling_ratio` | float | ratio | Swelling ratio in aqueous medium |

### Degradation

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `degrad_days_min` | int | days | Minimum degradation time (environment-dependent) |
| `degrad_days_max` | int | days | Maximum degradation time |
| `enzymatic_degradability` | bool | — | Susceptible to enzymatic degradation |
| `hydrolytic_stability` | enum | — | `low` / `med` / `high` — resistance to hydrolysis |

### Biological Safety

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `cytotoxicity_safe` | bool | — | Passes ISO 10993-5 cytotoxicity screening |
| `hemocompatible` | bool | — | Blood-contact compatible |
| `antimicrobial` | bool | — | Inherent antimicrobial activity |
| `endotoxin_concern` | text | — | Endotoxin contamination risk level |

### Sterilization Compatibility

| Column | Type | Description |
|--------|------|-------------|
| `ster_gamma` | bool | Compatible with gamma irradiation (25–40 kGy) |
| `ster_eto` | bool | Compatible with ethylene oxide |
| `ster_steam` | bool | Compatible with steam sterilization (121°C) |
| `ster_uv` | bool | Compatible with UV sterilization |
| `ster_autoclave` | bool | Compatible with autoclaving (134°C) |

### Processing Methods

| Column | Type | Description |
|--------|------|-------------|
| `proc_film` | bool | Can be formed into thin films |
| `proc_casting` | bool | Compatible with solution casting |
| `proc_extrusion` | bool | Compatible with extrusion processing |
| `proc_coating` | bool | Can be used as a coating |
| `proc_melt` | bool | Compatible with melt processing |
| `solvent_compatible` | text | Compatible solvents and processing media |

### Cost & Availability

| Column | Type | Description |
|--------|------|-------------|
| `cost_band` | enum | `low` / `med` / `high` — approximate cost tier |
| `availability_band` | enum | `low` / `med` / `high` — commercial availability |

---

## Evidence Levels

| Level | Meaning | Typical Sources |
|-------|---------|-----------------|
| `high` | Well-characterized in peer-reviewed literature, multiple independent studies | >5 peer-reviewed publications with consistent data |
| `med` | Reported in literature but fewer sources or wider property ranges | 2–5 publications, or manufacturer datasheets |
| `low` | Limited data, single source, or estimated from analogous materials | 1 publication, blends with extrapolated properties |

---

## Data Sources

Properties were compiled from peer-reviewed literature. Key references include:

- **Chitosan**: [doi:10.1016/j.carbpol.2020.116066](https://doi.org/10.1016/j.carbpol.2020.116066)
- **Alginate**: [doi:10.1016/j.ijbiomac.2021.01.032](https://doi.org/10.1016/j.ijbiomac.2021.01.032)
- **Cellulose**: [doi:10.1021/acs.chemrev.9b00480](https://doi.org/10.1021/acs.chemrev.9b00480)
- **Starch**: [doi:10.1016/j.foodhyd.2020.106389](https://doi.org/10.1016/j.foodhyd.2020.106389)
- **Pectin**: [doi:10.1016/j.foodhyd.2018.12.043](https://doi.org/10.1016/j.foodhyd.2018.12.043)
- **Hyaluronic Acid**: [doi:10.1016/j.biomaterials.2020.120286](https://doi.org/10.1016/j.biomaterials.2020.120286)
- **Pullulan**: [doi:10.1016/j.foodhyd.2019.105632](https://doi.org/10.1016/j.foodhyd.2019.105632)
- **Dextran**: [doi:10.1016/j.eurpolymj.2019.109259](https://doi.org/10.1016/j.eurpolymj.2019.109259)
- **Gellan**: [doi:10.1016/j.carbpol.2021.117555](https://doi.org/10.1016/j.carbpol.2021.117555)
- **Agar**: [doi:10.1016/j.foodhyd.2020.105775](https://doi.org/10.1016/j.foodhyd.2020.105775)
- **Carrageenan**: [doi:10.1016/j.carbpol.2020.116992](https://doi.org/10.1016/j.carbpol.2020.116992)
- **Guar/Xanthan**: [doi:10.1016/j.foodhyd.2019.105190](https://doi.org/10.1016/j.foodhyd.2019.105190), [doi:10.1016/j.foodhyd.2020.105925](https://doi.org/10.1016/j.foodhyd.2020.105925)
- **CMC/HPMC**: [doi:10.1016/j.carbpol.2021.117890](https://doi.org/10.1016/j.carbpol.2021.117890)
- **Konjac**: [doi:10.1016/j.foodhyd.2018.10.021](https://doi.org/10.1016/j.foodhyd.2018.10.021)

---

## Data Classification

> [!WARNING]
> All values in the starter dataset are **screening-grade approximations** derived from published literature.
> They are **NOT** certified, tested, or verified specifications. Property values are **starter data** intended
> to demonstrate the screening engine and should be replaced with actual test results for production use.

| Aspect | Status |
|--------|--------|
| Values | Approximate — compiled from literature ranges |
| Formulation dependency | **Critical** — same polymer varies dramatically with MW, plasticizer, crosslinking |
| Test conditions | Assumed standard (23°C / 50% RH) unless noted |
| Sterilization | General tolerance — properties may change post-sterilization |
| Evidence level | Indicated per material (`low`/`med`/`high`) |

---

## Missing-Value Policy

The scoring engine handles missing (empty/null) values as follows:

| Column Type | If Missing | Scoring Behavior |
|-------------|-----------|------------------|
| `name` | Row skipped | Material not loaded |
| `category` | Defaults to `"unknown"` | No impact on scoring |
| `evidence_level` | Defaults to `"low"` | Lower confidence score |
| Float properties (e.g., `tensile_min`, `wvtr`) | Parsed as `None` | Receives partial credit (0.3) with penalty; reduces `data_completeness` |
| Bool properties (e.g., `ster_gamma`, `cytotoxicity_safe`) | Parsed as `None` | **Not counted as True** — if a hard filter requires it, material is filtered out |
| Enum properties (e.g., `cost_band`, `hydrolytic_stability`) | Parsed as `None` | Receives partial credit; reduces `data_completeness` |
| `data_completeness` | Auto-computed | Ratio of non-null core properties to total expected properties (14 core fields) |

> [!NOTE]
> Missing data is **never silently treated as a match**. The scoring engine explicitly penalizes missing values
> through reduced scores (0.3 instead of a real match) and lower `data_completeness`, which feeds into the
> `confidence` score. This ensures materials with sparse data rank lower than well-characterized alternatives.

---

## Known Limitations

1. **Formulation dependence**: The same base polymer (e.g., "chitosan") can exhibit vastly different properties depending on molecular weight, degree of deacetylation, plasticizer ratio, and solvent system used during film formation.

2. **Test condition variability**: Literature values for WVTR and OTR vary by test temperature, humidity, and film thickness. Values in this dataset assume standard conditions (23°C, 50% RH for WVTR; 23°C, 0% RH for OTR) unless noted.

3. **Degradation timelines**: Real degradation rates depend on the biological environment (soil, composting, marine, physiological) and are reported as approximate ranges.

4. **Blends and composites**: Materials labeled as "blends" (e.g., Chitosan-PVA) have properties estimated from literature reporting similar blend ratios. Actual properties will vary with the specific formulation.

5. **Sterilization compatibility**: Boolean values indicate general tolerance. Some materials may survive sterilization but with altered properties (e.g., reduced molecular weight after gamma irradiation).

