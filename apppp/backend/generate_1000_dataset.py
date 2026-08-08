#!/usr/bin/env python3
import os
import json
import random
import csv
import pymysql

# Set seed for reproducible realistic dataset
random.seed(42)

BASE_CATEGORIES = [
    "Chitosan & Derivatives",
    "Alginate & Salts",
    "Hyaluronic Acid & Hyaluronates",
    "Cellulose & Nanocellulose",
    "Pectin & Pectinates",
    "Starch & Modified Starches",
    "Agarose & Agars",
    "Dextran & Dextran Esters",
    "Pullulan & Exopolysaccharides",
    "Carrageenan (Kappa, Iota, Lambda)",
    "Xanthan & Gellan Gums",
    "Chondroitin & Glycosaminoglycans",
    "Biopolymer Blends & Composites"
]

SOURCES = [
    "Crustacean shells (Crab/Shrimp)",
    "Fungal fermentation (Aspergillus niger)",
    "Brown Seaweed (Laminaria hyperborea)",
    "Bacterial fermentation (Streptococcus zooepidemicus)",
    "Wood pulp / Cotton linters",
    "Citrus peel / Apple pomace",
    "Corn starch / Potato starch",
    "Red Seaweed (Rhodophyta)",
    "Leuconostoc mesenteroides fermentation",
    "Aureobasidium pullulans culture",
    "Xanthomonas campestris culture",
    "Sphingomonas elodea culture",
    "Porcine cartilage",
    "Recombinant yeast production"
]

EVIDENCE_LEVELS = ["low", "med", "high"]
BANDS = ["low", "med", "high"]
STABILITY = ["low", "med", "high"]

PREFIXES = [
    "Ultra-Pure", "High-MW", "Low-MW", "Crosslinked", "Carboxymethylated", 
    "Quaternized", "Sulfated", "Methacrylated", "Nanofibrillated", "Phosphate-modified",
    "Biomedical Grade", "Pharma-Grade", "Injectable Grade", "Film-Forming", "Hydrogel-Grade"
]

PREFIXES_SHORT = [
    "Alpha", "Beta", "Gamma", "Nano", "Micro", "Bio", "Synthe", "Eco", "Pro", "Flex"
]

def generate_records(count=1000):
    records = []

    for i in range(1, count + 1):
        mat_id = f"mat-{i:04d}"
        cat = random.choice(BASE_CATEGORIES)
        prefix = random.choice(PREFIXES)
        base_name = cat.split("&")[0].strip()
        name = f"{prefix} {base_name} Type-{random.randint(100, 999)}"
        source = random.choice(SOURCES)
        evidence = random.choices(EVIDENCE_LEVELS, weights=[0.2, 0.5, 0.3])[0]
        notes = f"High-purity biomedical grade {base_name.lower()} engineered for tissue engineering, drug delivery, and barrier applications."

        # Mechanical Properties
        ts_min = round(random.uniform(5.0, 45.0), 2)
        ts_max = round(ts_min + random.uniform(5.0, 50.0), 2)
        em_min = round(random.uniform(0.1, 3.5), 2)
        em_max = round(em_min + random.uniform(0.2, 4.0), 2)
        elo_min = round(random.uniform(5.0, 60.0), 2)
        elo_max = round(elo_min + random.uniform(10.0, 150.0), 2)
        puncture = round(random.uniform(1.5, 35.0), 2)

        # Barrier Properties
        wvtr = round(random.uniform(150.0, 2500.0), 1)
        otr = round(random.uniform(10.0, 450.0), 1)

        # Biological & Degradation
        water_sol = random.choice([True, False])
        swelling = round(random.uniform(1.2, 18.0), 2)
        deg_min = random.randint(7, 90)
        deg_max = deg_min + random.randint(14, 270)
        enzymatic = random.choice([True, False])
        hydrolytic = random.choice(STABILITY)

        cyto_safe = random.choices([True, False], weights=[0.9, 0.1])[0]
        hemo_comp = random.choices([True, False], weights=[0.85, 0.15])[0]
        antimicrobial = random.choices([True, False], weights=[0.4, 0.6])[0]
        endotoxin = random.choice(["Low (<0.1 EU/mg)", "Ultra-Low (<0.05 EU/mg)", "Standard (<0.5 EU/mg)"])

        # Sterilization & Processing
        ster_gamma = random.choice([True, False])
        ster_eto = random.choice([True, False])
        ster_steam = random.choice([True, False])
        ster_uv = random.choice([True, False])
        ster_autoclave = random.choice([True, False])

        proc_film = random.choice([True, False])
        proc_casting = random.choice([True, False])
        proc_extrusion = random.choice([True, False])
        proc_coating = random.choice([True, False])
        proc_melt = random.choice([True, False])

        solvent = random.choice(["Water, Dilute Acetic Acid", "Phosphate Buffered Saline", "Ethanol/Water 70:30", "DMSO, Water"])
        cost_band = random.choice(BANDS)
        avail_band = random.choice(BANDS)
        completeness = round(random.uniform(0.85, 1.0), 2)

        record = {
            "id": mat_id,
            "name": name,
            "category": cat,
            "source": source,
            "notes": notes,
            "evidenceLevel": evidence,
            "tensileStrengthMpaMin": ts_min,
            "tensileStrengthMpaMax": ts_max,
            "elasticModulusGpaMin": em_min,
            "elasticModulusGpaMax": em_max,
            "elongationPctMin": elo_min,
            "elongationPctMax": elo_max,
            "punctureResistanceN": puncture,
            "wvtr": wvtr,
            "otr": otr,
            "waterSolubility": water_sol,
            "swellingRatio": swelling,
            "degradationDaysMin": deg_min,
            "degradationDaysMax": deg_max,
            "enzymaticDegradability": enzymatic,
            "hydrolyticStability": hydrolytic,
            "cytotoxicitySafe": cyto_safe,
            "hemocompatible": hemo_comp,
            "antimicrobial": antimicrobial,
            "endotoxinConcern": endotoxin,
            "sterGamma": ster_gamma,
            "sterEto": ster_eto,
            "sterSteam": ster_steam,
            "sterUv": ster_uv,
            "sterAutoclave": ster_autoclave,
            "procFilm": proc_film,
            "procCasting": proc_casting,
            "procExtrusion": proc_extrusion,
            "procCoating": proc_coating,
            "procMelt": proc_melt,
            "solventCompatible": solvent,
            "costBand": cost_band,
            "availabilityBand": avail_band,
            "dataCompleteness": completeness
        }
        records.append(record)

    return records

def save_csv(records, filepath):
    if not records:
        return
    headers = list(records[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(records)
    print(f"✅ Saved CSV file to: {filepath} ({len(records)} records)")

def save_json(records, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"✅ Saved JSON file to: {filepath} ({len(records)} records)")

def seed_mariadb(records, db_pass="meheer17"):
    try:
        conn = pymysql.connect(
            host="localhost",
            port=3306,
            user="root",
            password=db_pass,
            database="polysaccharide_selector"
        )
        cur = conn.cursor()

        # Clear existing
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cur.execute("TRUNCATE TABLE material_properties;")
        cur.execute("TRUNCATE TABLE materials;")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")

        materials_sql = """
        INSERT INTO materials (id, name, category, source, notes, evidence_level, material_references, ext_properties)
        VALUES (%s, %s, %s, %s, %s, %s, '[]', '{}')
        """

        props_sql = """
        INSERT INTO material_properties (
            id, material_id, tensile_strength_mpa_min, tensile_strength_mpa_max,
            elastic_modulus_gpa_min, elastic_modulus_gpa_max, elongation_pct_min,
            elongation_pct_max, puncture_resistance_n, wvtr, otr, water_solubility,
            swelling_ratio, degradation_days_min, degradation_days_max,
            enzymatic_degradability, hydrolytic_stability, cytotoxicity_safe,
            hemocompatible, antimicrobial, endotoxin_concern, ster_gamma, ster_eto,
            ster_steam, ster_uv, ster_autoclave, proc_film, proc_casting, proc_extrusion,
            proc_coating, proc_melt, solvent_compatible, cost_band, availability_band,
            data_completeness
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        mat_rows = []
        prop_rows = []

        for r in records:
            m_id = r["id"]
            p_id = f"prop-{m_id}"

            mat_rows.append((
                m_id, r["name"], r["category"], r["source"], r["notes"], r["evidenceLevel"]
            ))

            prop_rows.append((
                p_id, m_id, r["tensileStrengthMpaMin"], r["tensileStrengthMpaMax"],
                r["elasticModulusGpaMin"], r["elasticModulusGpaMax"], r["elongationPctMin"],
                r["elongationPctMax"], r["punctureResistanceN"], r["wvtr"], r["otr"],
                1 if r["waterSolubility"] else 0, r["swellingRatio"], r["degradationDaysMin"],
                r["degradationDaysMax"], 1 if r["enzymaticDegradability"] else 0,
                r["hydrolyticStability"], 1 if r["cytotoxicitySafe"] else 0,
                1 if r["hemocompatible"] else 0, 1 if r["antimicrobial"] else 0,
                r["endotoxinConcern"], 1 if r["sterGamma"] else 0, 1 if r["sterEto"] else 0,
                1 if r["sterSteam"] else 0, 1 if r["sterUv"] else 0, 1 if r["sterAutoclave"] else 0,
                1 if r["procFilm"] else 0, 1 if r["procCasting"] else 0, 1 if r["procExtrusion"] else 0,
                1 if r["procCoating"] else 0, 1 if r["procMelt"] else 0, r["solventCompatible"],
                r["costBand"], r["availabilityBand"], r["dataCompleteness"]
            ))

        cur.executemany(materials_sql, mat_rows)
        cur.executemany(props_sql, prop_rows)
        conn.commit()
        conn.close()
        print(f"✅ Successfully seeded {len(records)} material records into MariaDB 'polysaccharide_selector'!")
    except Exception as e:
        print(f"❌ Error seeding MariaDB: {e}")

if __name__ == "__main__":
    records = generate_records(1000)

    # 1. Save CSV
    csv_path_backend = "/home/mahi17/Github/PDD/apppp/backend/biopolymer_materials_1000.csv"
    csv_path_root = "/home/mahi17/Github/PDD/biopolymer_materials_1000.csv"
    save_csv(records, csv_path_backend)
    save_csv(records, csv_path_root)

    # 2. Save JSON for Android Assets
    json_path_android = "/home/mahi17/Github/PDD/apppp/android/app/src/main/assets/offline_catalog_50.json"
    save_json(records, json_path_android)

    # 3. Seed MariaDB
    seed_mariadb(records)
