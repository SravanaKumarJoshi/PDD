"""
Dataset augmentation module.
Generates 200+ polysaccharide entries from literature-sourced base materials
with controlled property variation.
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Seed for reproducibility
RNG = np.random.default_rng(42)

# Base materials with realistic property ranges from published literature.
# Each tuple: (name, category, tensile_min, tensile_max, modulus_min, modulus_max,
#   elongation_min, elongation_max, flex_min, flex_max, wvtr_min, wvtr_max,
#   o2perm_min, o2perm_max, biocompat, toxicity_score, antimicrobial,
#   biodeg_min, biodeg_max, env_impact, solubility, film_forming,
#   ster_gamma, ster_eto, ster_steam, cost_band, avail_band,
#   evidence_level, source_doi, suitability)
BASE_MATERIALS = [
    ("Chitosan High MW", "chitosan", 50, 100, 1.5, 4.0, 5, 30, 6, 8, 150, 250, 80, 110, 9, 9, 1, 30, 180, 8, "low", 1, 1, 1, 0, "low", "high", "high", "10.1016/j.carbpol.2020.116066", 1),
    ("Chitosan Low MW", "chitosan", 15, 50, 0.5, 2.0, 10, 45, 7, 9, 200, 300, 100, 150, 9, 9, 1, 14, 90, 8, "high", 1, 1, 1, 0, "low", "high", "med", "10.1016/j.carbpol.2020.116066", 1),
    ("Chitosan-PVA Blend", "chitosan", 40, 120, 1.5, 5.0, 15, 60, 7, 9, 100, 160, 60, 90, 9, 9, 1, 60, 270, 7, "low", 1, 1, 1, 0, "med", "high", "low", "10.1016/j.ijbiomac.2019.09.144", 1),
    ("Chitin Nanowhisker", "chitosan", 100, 250, 8.0, 20.0, 1, 5, 3, 5, 50, 80, 20, 35, 8, 8, 0, 180, 365, 8, "low", 1, 1, 1, 1, "med", "low", "low", "10.1016/j.carbpol.2020.116066", 1),
    ("Sodium Alginate", "alginate", 20, 80, 0.5, 2.5, 4, 20, 7, 9, 300, 400, 100, 140, 8, 8, 0, 7, 90, 9, "high", 1, 0, 1, 1, "low", "high", "high", "10.1016/j.ijbiomac.2021.01.032", 1),
    ("Calcium Alginate", "alginate", 35, 110, 1.0, 3.5, 3, 15, 6, 8, 170, 250, 60, 100, 8, 8, 0, 14, 120, 9, "low", 1, 1, 1, 1, "low", "high", "high", "10.1016/j.ijbiomac.2021.01.032", 1),
    ("Cellulose Nanocrystal", "cellulose", 80, 200, 5.0, 15.0, 2, 10, 3, 5, 40, 70, 20, 40, 9, 9, 0, 180, 365, 9, "low", 1, 1, 1, 1, "med", "high", "high", "10.1021/acs.chemrev.9b00480", 1),
    ("Cellulose Nanofiber", "cellulose", 60, 150, 3.0, 10.0, 5, 20, 5, 7, 60, 100, 35, 65, 9, 9, 0, 120, 365, 9, "low", 1, 1, 1, 1, "med", "high", "high", "10.1021/acs.chemrev.9b00480", 1),
    ("Bacterial Cellulose", "cellulose", 100, 300, 10.0, 30.0, 1, 8, 3, 5, 30, 55, 15, 30, 9, 10, 0, 365, 730, 9, "low", 1, 1, 1, 1, "high", "low", "med", "10.1016/j.carbpol.2019.115549", 1),
    ("CMC", "cellulose", 20, 60, 0.5, 3.0, 5, 30, 6, 8, 300, 400, 120, 170, 9, 9, 0, 30, 180, 8, "high", 1, 1, 1, 1, "low", "high", "high", "10.1016/j.carbpol.2021.117890", 1),
    ("HPMC", "cellulose", 30, 80, 1.0, 4.0, 5, 20, 6, 8, 150, 220, 60, 100, 9, 9, 0, 60, 365, 8, "high", 1, 1, 1, 1, "med", "high", "high", "10.1016/j.carbpol.2021.117890", 1),
    ("Thermoplastic Starch", "starch", 2, 15, 0.05, 0.5, 20, 200, 8, 10, 500, 700, 300, 450, 8, 8, 0, 30, 180, 9, "high", 1, 0, 1, 0, "low", "high", "high", "10.1016/j.foodhyd.2020.106389", 0),
    ("Starch Nanocrystal", "starch", 30, 80, 1.0, 4.0, 3, 15, 5, 7, 120, 180, 70, 110, 8, 8, 0, 60, 240, 8, "low", 1, 1, 1, 0, "low", "high", "med", "10.1016/j.foodhyd.2020.106389", 1),
    ("Oxidized Starch", "starch", 10, 40, 0.2, 1.5, 10, 80, 7, 9, 350, 460, 200, 300, 7, 7, 0, 14, 90, 8, "high", 1, 0, 1, 0, "low", "high", "low", "10.1016/j.foodhyd.2020.106389", 0),
    ("High-Methoxyl Pectin", "pectin", 15, 50, 0.3, 2.0, 5, 25, 6, 8, 250, 350, 120, 170, 7, 7, 0, 14, 60, 8, "high", 1, 0, 1, 1, "low", "high", "high", "10.1016/j.foodhyd.2018.12.043", 1),
    ("Low-Methoxyl Pectin", "pectin", 25, 70, 0.5, 3.0, 3, 15, 5, 7, 170, 250, 80, 120, 7, 7, 0, 21, 90, 8, "high", 1, 0, 1, 1, "low", "high", "med", "10.1016/j.foodhyd.2018.12.043", 1),
    ("Hyaluronic Acid", "hyaluronic_acid", 1, 5, 0.01, 0.1, 100, 500, 9, 10, 8000, 10000, 8000, 10000, 10, 10, 0, 1, 30, 7, "high", 1, 1, 1, 1, "high", "med", "high", "10.1016/j.biomaterials.2020.120286", 1),
    ("Crosslinked HA", "hyaluronic_acid", 3, 10, 0.05, 0.3, 50, 200, 8, 10, 4000, 6000, 4000, 6000, 10, 10, 0, 30, 365, 7, "low", 1, 1, 1, 1, "high", "low", "med", "10.1016/j.biomaterials.2020.120286", 1),
    ("Pullulan", "pullulan", 15, 40, 0.5, 2.0, 5, 30, 6, 8, 250, 350, 3, 8, 8, 8, 0, 30, 120, 8, "high", 1, 1, 1, 1, "med", "med", "med", "10.1016/j.foodhyd.2019.105632", 1),
    ("Pullulan-Chitosan Blend", "pullulan", 25, 60, 0.8, 3.0, 8, 25, 6, 8, 170, 240, 5, 15, 8, 8, 1, 30, 150, 8, "low", 1, 1, 1, 0, "med", "med", "low", "10.1016/j.foodhyd.2019.105632", 1),
    ("Dextran", "dextran", 5, 20, 0.1, 0.8, 50, 300, 8, 10, 700, 900, 400, 600, 9, 9, 0, 1, 14, 7, "high", 1, 1, 1, 1, "med", "high", "high", "10.1016/j.eurpolymj.2019.109259", 1),
    ("Dextran Methacrylate", "dextran", 10, 40, 0.3, 1.5, 20, 100, 7, 9, 350, 470, 160, 250, 8, 8, 0, 14, 180, 7, "low", 1, 1, 1, 1, "high", "low", "low", "10.1016/j.eurpolymj.2019.109259", 0),
    ("Gellan Gum High Acyl", "gellan", 5, 20, 0.05, 0.5, 30, 150, 8, 10, 430, 560, 250, 350, 8, 8, 0, 7, 60, 8, "high", 1, 0, 1, 1, "low", "high", "med", "10.1016/j.carbpol.2021.117555", 0),
    ("Gellan Gum Low Acyl", "gellan", 15, 50, 0.5, 2.5, 2, 10, 4, 6, 170, 250, 80, 120, 8, 8, 0, 14, 120, 8, "low", 1, 1, 1, 1, "low", "high", "med", "10.1016/j.carbpol.2021.117555", 1),
    ("Agar", "agar", 20, 60, 0.5, 3.0, 2, 12, 4, 6, 210, 300, 100, 140, 7, 7, 0, 30, 180, 8, "low", 1, 1, 1, 1, "low", "high", "high", "10.1016/j.foodhyd.2020.105775", 1),
    ("Agarose", "agar", 25, 70, 0.8, 4.0, 1, 8, 3, 5, 150, 220, 60, 100, 9, 9, 0, 60, 365, 8, "low", 1, 1, 1, 1, "med", "med", "high", "10.1016/j.foodhyd.2020.105775", 1),
    ("Kappa-Carrageenan", "carrageenan", 20, 70, 0.5, 3.0, 3, 15, 5, 7, 170, 250, 80, 120, 7, 7, 0, 30, 180, 8, "low", 1, 1, 1, 1, "low", "high", "high", "10.1016/j.carbpol.2020.116992", 1),
    ("Iota-Carrageenan", "carrageenan", 10, 40, 0.2, 1.5, 10, 50, 7, 9, 300, 400, 150, 210, 7, 7, 0, 14, 120, 8, "high", 1, 0, 1, 1, "low", "high", "high", "10.1016/j.carbpol.2020.116992", 0),
    ("Lambda-Carrageenan", "carrageenan", 2, 10, 0.05, 0.3, 50, 200, 8, 10, 430, 560, 250, 350, 6, 6, 0, 7, 60, 7, "high", 1, 0, 1, 0, "low", "high", "med", "10.1016/j.carbpol.2020.116992", 0),
    ("Guar Gum", "guar", 5, 25, 0.1, 0.8, 20, 100, 7, 9, 520, 660, 300, 400, 7, 7, 0, 7, 60, 8, "high", 1, 0, 1, 0, "low", "high", "high", "10.1016/j.foodhyd.2019.105190", 0),
    ("Hydroxypropyl Guar", "guar", 8, 30, 0.15, 1.0, 15, 80, 7, 9, 390, 510, 200, 300, 7, 7, 0, 14, 90, 8, "high", 1, 0, 1, 0, "med", "med", "low", "10.1016/j.foodhyd.2019.105190", 0),
    ("Xanthan Gum", "xanthan", 3, 15, 0.05, 0.5, 30, 150, 8, 10, 430, 560, 250, 350, 7, 7, 0, 14, 90, 7, "high", 1, 0, 1, 0, "low", "high", "high", "10.1016/j.foodhyd.2020.105925", 0),
    ("Xanthan-Guar Blend", "xanthan", 10, 35, 0.2, 1.2, 15, 60, 7, 9, 300, 400, 160, 240, 7, 7, 0, 14, 120, 7, "high", 1, 0, 1, 0, "low", "high", "low", "10.1016/j.foodhyd.2020.105925", 0),
    ("Konjac Glucomannan", "glucomannan", 10, 40, 0.2, 1.5, 15, 80, 7, 9, 350, 460, 160, 240, 7, 7, 0, 14, 90, 8, "high", 1, 0, 1, 0, "low", "med", "med", "10.1016/j.foodhyd.2018.10.021", 0),
    ("Fucoidan", "fucoidan", 5, 15, 0.1, 0.5, 20, 80, 6, 8, 500, 650, 300, 420, 9, 9, 1, 7, 60, 8, "high", 0, 0, 1, 0, "med", "low", "med", "10.1016/j.ijbiomac.2020.07.235", 0),
]


def _sample_in_range(lo, hi, n):
    """Sample n values uniformly in [lo, hi]."""
    return RNG.uniform(lo, hi, size=n)


def generate_dataset(n_variants=5, output_path=None):
    """Generate expanded dataset with controlled augmentation."""
    rows = []
    for mat in BASE_MATERIALS:
        (name, cat, ts_lo, ts_hi, em_lo, em_hi, el_lo, el_hi,
         fl_lo, fl_hi, wv_lo, wv_hi, o2_lo, o2_hi, biocompat,
         tox, antimicro, bd_lo, bd_hi, env_imp, sol, film,
         sg, se, ss, cost, avail, evid, doi, suit) = mat

        # Base (real) entry — midpoint of ranges
        base = _make_row(
            name, cat,
            (ts_lo + ts_hi) / 2, (em_lo + em_hi) / 2,
            (el_lo + el_hi) / 2, (fl_lo + fl_hi) / 2,
            (wv_lo + wv_hi) / 2, (o2_lo + o2_hi) / 2,
            biocompat, tox, antimicro,
            int((bd_lo + bd_hi) / 2), env_imp,
            sol, film, sg, se, ss, cost, avail, evid, doi,
            False, suit
        )
        rows.append(base)

        # Augmented variants
        ts_vals = _sample_in_range(ts_lo, ts_hi, n_variants)
        em_vals = _sample_in_range(em_lo, em_hi, n_variants)
        el_vals = _sample_in_range(el_lo, el_hi, n_variants)
        fl_vals = _sample_in_range(fl_lo, fl_hi, n_variants)
        wv_vals = _sample_in_range(wv_lo, wv_hi, n_variants)
        o2_vals = _sample_in_range(o2_lo, o2_hi, n_variants)
        bd_vals = RNG.integers(bd_lo, bd_hi + 1, size=n_variants)
        bio_vals = np.clip(RNG.normal(biocompat, 0.5, n_variants), 1, 10).astype(int)
        tox_vals = np.clip(RNG.normal(tox, 0.3, n_variants), 1, 10).astype(int)

        for i in range(n_variants):
            vname = f"{name} V{i+1}"
            aug_evid = "low" if evid == "high" else "low"
            row = _make_row(
                vname, cat,
                round(ts_vals[i], 1), round(em_vals[i], 2),
                round(el_vals[i], 1), round(fl_vals[i], 1),
                round(wv_vals[i], 1), round(o2_vals[i], 1),
                int(bio_vals[i]), int(tox_vals[i]), antimicro,
                int(bd_vals[i]), env_imp,
                sol, film, sg, se, ss, cost, avail, aug_evid, doi,
                True, suit
            )
            rows.append(row)

    df = pd.DataFrame(rows)
    # Compute data_completeness
    required = ["tensile_strength", "elastic_modulus", "elongation_pct",
                "flexibility", "wvtr", "oxygen_permeability",
                "biocompatibility", "biodegradation_days"]
    df["data_completeness"] = df[required].notna().mean(axis=1).round(2)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Generated {len(df)} materials -> {output_path}")

    return df


def _make_row(name, cat, ts, em, el, fl, wv, o2, bio, tox, anti,
              bd, env, sol, film, sg, se, ss, cost, avail, evid,
              doi, is_aug, suit):
    return {
        "polymer": name,
        "category": cat,
        "tensile_strength": round(ts, 1),
        "elastic_modulus": round(em, 2),
        "elongation_pct": round(el, 1),
        "flexibility": round(fl, 1),
        "wvtr": round(wv, 1),
        "oxygen_permeability": round(o2, 1),
        "biocompatibility": int(bio),
        "toxicity_score": int(tox),
        "antimicrobial": int(anti),
        "biodegradation_days": int(bd),
        "environmental_impact": int(env),
        "solubility": sol,
        "film_forming": int(film),
        "sterilization_gamma": int(sg),
        "sterilization_eto": int(se),
        "sterilization_steam": int(ss),
        "cost_band": cost,
        "availability_band": avail,
        "evidence_level": evid,
        "source_doi": doi,
        "is_augmented": int(is_aug),
        "suitability_label": int(suit),
    }


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "data" / "polymers.csv"
    generate_dataset(n_variants=5, output_path=out)
