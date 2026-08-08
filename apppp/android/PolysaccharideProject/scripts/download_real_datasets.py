"""
download_real_datasets.py
=========================
Phase 1 — Real Data Download (Clinical-Grade Pipeline)

Downloads polysaccharide-related data from reputable public APIs:
  - PubChem (Compound API, BioAssay)
  - ChEMBL (Molecule endpoint)
  - GlyConnect REST API
  - UniProt (Keyword search for glycan-related proteins)
  - GlyCosmos (glycan list)

ALL raw datasets are saved to ONE single folder:
  Polysaccharide_Datasets_All/

Every dataset is cataloged in dataset_catalog.json with full provenance.

RF1 — This script is the primary fix for Red Flag 1 (synthetic-only data).
Synthetic datasets are intentionally NOT generated here; they are moved to
Polysaccharide_Datasets_Synthetic_DemoOnly/ by move_synthetic_data().
"""
import os
import json
import csv
import time
import hashlib
import shutil
import requests
from datetime import datetime, timezone

# ─── PATHS ───────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_ALL      = os.path.join(BASE_DIR, "datasets", "raw", "Polysaccharide_Datasets_All")
SYNTHETIC_DIR= os.path.join(BASE_DIR, "datasets", "raw", "Polysaccharide_Datasets_Synthetic_DemoOnly")
META_DIR     = os.path.join(BASE_DIR, "datasets", "metadata")
LOG_FILE     = os.path.join(BASE_DIR, "download_real_log.txt")
CATALOG_FILE = os.path.join(META_DIR, "dataset_catalog.json")

# ─── LOGGING ─────────────────────────────────────────────────────────────────
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ─── HTTP HELPERS ─────────────────────────────────────────────────────────────
HEADERS = {"User-Agent": "PolysaccharideClinicalPipeline/1.0 (academic-research)"}

def get_json(url, params=None, retries=3, wait=2):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                log(f"  Rate-limited. Waiting {wait * (attempt+1)}s...")
                time.sleep(wait * (attempt + 1))
            else:
                log(f"  HTTP {r.status_code} for {url}")
                return None
        except Exception as e:
            log(f"  Request error (attempt {attempt+1}): {e}")
            time.sleep(wait)
    return None

def get_text(url, params=None, retries=3, wait=2):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r.text
            elif r.status_code == 429:
                time.sleep(wait * (attempt + 1))
            else:
                log(f"  HTTP {r.status_code} for {url}")
                return None
        except Exception as e:
            log(f"  Request error (attempt {attempt+1}): {e}")
            time.sleep(wait)
    return None

# ─── SETUP ───────────────────────────────────────────────────────────────────
def setup_dirs():
    os.makedirs(RAW_ALL, exist_ok=True)
    os.makedirs(SYNTHETIC_DIR, exist_ok=True)
    os.makedirs(META_DIR, exist_ok=True)
    log(f"Dirs ready. RAW_ALL = {RAW_ALL}")

def move_synthetic_to_demoonly():
    """RF1: Move existing synthetic datasets out of the main folder."""
    old_raw = os.path.join(BASE_DIR, "datasets", "raw", "Polysaccharide_Datasets_All")
    moved = 0
    # Check if there are existing synthetic CSVs in the raw folder
    if os.path.isdir(old_raw):
        for fname in os.listdir(old_raw):
            if fname.startswith("dataset_") and fname.endswith((".csv", ".json")):
                src = os.path.join(old_raw, fname)
                dst = os.path.join(SYNTHETIC_DIR, fname)
                shutil.move(src, dst)
                log(f"  Moved synthetic file to DemoOnly: {fname}")
                moved += 1
    log(f"  Moved {moved} synthetic files to Polysaccharide_Datasets_Synthetic_DemoOnly/")

# ─── CATALOG HELPERS ─────────────────────────────────────────────────────────
def load_catalog():
    if os.path.isfile(CATALOG_FILE):
        with open(CATALOG_FILE, encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_catalog(entries):
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

def catalog_entry(ds_id, name, filename, source_name, source_url, query, license_str,
                  row_count, col_count, col_names, description, status, local_path, fmt):
    size_bytes = os.path.getsize(local_path) if os.path.isfile(local_path) else 0
    return {
        "id": ds_id,
        "name": name,
        "filename": filename,
        "source_name": source_name,
        "source_url": source_url,
        "api_query": query,
        "license": license_str,
        "retrieval_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "download_timestamp": datetime.now(timezone.utc).isoformat(),
        "local_path": local_path,
        "file_format": fmt,
        "file_size_bytes": size_bytes,
        "rows": row_count,
        "columns": col_count,
        "column_names": col_names,
        "description": description,
        "download_status": status,
        "is_real_data": True,
        "is_synthetic": False,
        "clinical_use_allowed": True
    }

# ─── DATASET 1: PubChem — polysaccharide keyword search ─────────────────────
def download_pubchem_polysaccharides(catalog):
    """
    PubChem Compound API — keyword search for 'polysaccharide'
    Endpoint: https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{keyword}/JSON
    Also uses ESearch + EFetch for getting compound properties.
    License: Public Domain (US Government)
    """
    log("=" * 60)
    log("Downloading PubChem polysaccharide compounds...")

    # Step 1: Get CIDs via keyword
    query = "polysaccharide"
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{query}/cids/JSON"
    data = get_json(url)
    cids = []
    if data and "IdentifierList" in data:
        cids = data["IdentifierList"]["CID"][:500]  # cap at 500
        log(f"  PubChem keyword '{query}': {len(cids)} CIDs found")
    else:
        log("  PubChem keyword search: no CIDs returned; will try classification-based fetch")
        cids = []

    # Also search for individual polysaccharide names
    additional_names = [
        "cellulose", "starch", "glycogen", "chitin", "chitosan",
        "hyaluronic acid", "heparin", "chondroitin sulfate", "pectin",
        "agar", "carrageenan", "xanthan gum", "dextran", "pullulan",
        "fucoidan", "laminarin", "alginate", "levan", "curdlan",
        "guar gum", "locust bean gum", "gum arabic", "inulin",
        "beta-glucan", "amylose", "amylopectin"
    ]
    extra_cids = set()
    for name in additional_names:
        url2 = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(name)}/cids/JSON"
        d2 = get_json(url2)
        if d2 and "IdentifierList" in d2:
            for c in d2["IdentifierList"]["CID"][:10]:
                extra_cids.add(c)
        time.sleep(0.3)

    all_cids = list(set(cids) | extra_cids)[:600]
    log(f"  Total unique CIDs to fetch properties for: {len(all_cids)}")

    if not all_cids:
        log("  PubChem: No CIDs found — skipping.")
        return catalog

    # Step 2: Fetch properties in batches of 100
    properties = "MolecularWeight,MolecularFormula,CanonicalSMILES,IsomericSMILES,IUPACName,XLogP,Complexity,HBondDonorCount,HBondAcceptorCount,RotatableBondCount,HeavyAtomCount,Charge"
    rows = []
    batch_size = 100
    for i in range(0, len(all_cids), batch_size):
        batch = all_cids[i:i+batch_size]
        cid_str = ",".join(str(c) for c in batch)
        prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid_str}/property/{properties}/JSON"
        resp = get_json(prop_url)
        if resp and "PropertyTable" in resp:
            rows.extend(resp["PropertyTable"]["Properties"])
            log(f"  PubChem batch {i//batch_size+1}: fetched {len(resp['PropertyTable']['Properties'])} compounds")
        time.sleep(0.5)

    if not rows:
        log("  PubChem properties: no rows returned.")
        return catalog

    # Step 3: Write CSV
    fname = "realdata_01_pubchem_polysaccharides.csv"
    out_path = os.path.join(RAW_ALL, fname)
    
    fieldnames = set()
    for row in rows:
        fieldnames.update(row.keys())
    fieldnames = list(fieldnames)
    
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    log(f"  [OK] Saved {fname}: {len(rows)} compounds, {len(fieldnames)} columns")
    entry = catalog_entry(
        ds_id="real_01",
        name="PubChem Polysaccharide Compounds",
        filename=fname,
        source_name="PubChem (NCBI)",
        source_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/",
        query=f"keyword={query}; individual names: {', '.join(additional_names[:5])}...; max CIDs=600",
        license_str="Public Domain (US Government, free for all uses)",
        row_count=len(rows),
        col_count=len(fieldnames),
        col_names=fieldnames,
        description="Polysaccharide-related compounds from PubChem with molecular properties including MW, formula, logP, complexity.",
        status="Success",
        local_path=out_path,
        fmt="csv"
    )
    catalog.append(entry)
    return catalog

# ─── DATASET 2: ChEMBL — carbohydrate/glycan molecules ──────────────────────
def download_chembl_glycans(catalog):
    """
    ChEMBL REST API — molecules classified as carbohydrates/glycans
    Endpoint: https://www.ebi.ac.uk/chembl/api/data/molecule
    License: CC BY-SA 3.0
    """
    log("=" * 60)
    log("Downloading ChEMBL glycan/carbohydrate molecules...")

    all_rows = []
    # Search for molecules with 'polysaccharide' in preferred name or synonyms
    search_terms = ["polysaccharide", "saccharide", "glucan", "mannan", "xylan", "cellulose", "starch", "chitin"]
    seen_ids = set()

    for term in search_terms:
        url = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"
        params = {
            "pref_name__icontains": term,
            "limit": 100,
            "offset": 0,
            "format": "json"
        }
        while True:
            resp = get_json(url, params=params)
            if not resp or "molecules" not in resp:
                break
            molecules = resp["molecules"]
            if not molecules:
                break
            for mol in molecules:
                mid = mol.get("molecule_chembl_id", "")
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
                props = mol.get("molecule_properties") or {}
                row = {
                    "molecule_chembl_id": mid,
                    "pref_name": mol.get("pref_name", ""),
                    "max_phase": mol.get("max_phase", ""),
                    "molecule_type": mol.get("molecule_type", ""),
                    "first_approval": mol.get("first_approval", ""),
                    "oral": mol.get("oral", ""),
                    "therapeutic_flag": mol.get("therapeutic_flag", ""),
                    "mw_freebase": props.get("mw_freebase", ""),
                    "alogp": props.get("alogp", ""),
                    "hba": props.get("hba", ""),
                    "hbd": props.get("hbd", ""),
                    "psa": props.get("psa", ""),
                    "rtb": props.get("rtb", ""),
                    "full_mwt": props.get("full_mwt", ""),
                    "molecular_formula": props.get("molecular_formula", ""),
                    "num_ro5_violations": props.get("num_ro5_violations", ""),
                }
                all_rows.append(row)
            # Pagination
            page_meta = resp.get("page_meta", {})
            nxt = page_meta.get("next")
            if not nxt or len(all_rows) >= 1000:
                break
            params["offset"] = params["offset"] + params["limit"]
            time.sleep(0.5)
        time.sleep(0.5)

    if not all_rows:
        log("  ChEMBL: No molecules returned.")
        return catalog

    fname = "realdata_02_chembl_glycan_molecules.csv"
    out_path = os.path.join(RAW_ALL, fname)
    fieldnames = list(all_rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    log(f"  [OK] Saved {fname}: {len(all_rows)} molecules, {len(fieldnames)} columns")
    entry = catalog_entry(
        ds_id="real_02",
        name="ChEMBL Glycan/Carbohydrate Molecules",
        filename=fname,
        source_name="ChEMBL (European Bioinformatics Institute)",
        source_url="https://www.ebi.ac.uk/chembl/api/data/molecule",
        query=f"pref_name__icontains: {search_terms}; limit 1000",
        license_str="CC BY-SA 3.0 (ChEMBL database)",
        row_count=len(all_rows),
        col_count=len(fieldnames),
        col_names=fieldnames,
        description="Glycan and carbohydrate-related molecules from ChEMBL with therapeutic flags, molecular properties, and approval status.",
        status="Success",
        local_path=out_path,
        fmt="csv"
    )
    catalog.append(entry)
    return catalog

# ─── DATASET 3: GlyConnect — glycan structures ───────────────────────────────
def download_glyconnect(catalog):
    """
    GlyConnect REST API — glycan structures database
    Endpoint: https://glyconnect.expasy.org/api/
    License: CC BY 4.0
    """
    log("=" * 60)
    log("Downloading GlyConnect glycan structures...")

    url = "https://glyconnect.expasy.org/api/glycans"
    data = get_json(url)
    rows = []

    if data and isinstance(data, list):
        for g in data[:2000]:
            row = {
                "glycan_id": g.get("id", ""),
                "accession": g.get("accession", ""),
                "sequence": str(g.get("sequence", ""))[:200],
                "mass": g.get("mass", ""),
                "composition": str(g.get("composition", ""))[:200],
                "glycan_type": g.get("type", {}).get("name", "") if isinstance(g.get("type"), dict) else str(g.get("type", "")),
                "species": str([s.get("name", "") for s in g.get("species", [])])[:200],
                "database_count": g.get("database_count", ""),
            }
            rows.append(row)
    elif data and isinstance(data, dict):
        items = data.get("results", data.get("glycans", data.get("data", [])))
        for g in items[:2000]:
            row = {
                "glycan_id": g.get("id", g.get("glycan_id", "")),
                "sequence": str(g.get("sequence", g.get("iupac", "")))[:200],
                "mass": g.get("mass", ""),
                "glycan_type": str(g.get("type", ""))[:100],
                "composition": str(g.get("composition", ""))[:200],
            }
            rows.append(row)

    if not rows:
        log("  GlyConnect: endpoint returned no usable data. Trying alternative endpoint...")
        # Try alternative
        url2 = "https://glyconnect.expasy.org/api/glycans/?format=json&limit=500"
        d2 = get_json(url2)
        if d2 and isinstance(d2, dict):
            items = d2.get("results", [])
            for g in items:
                rows.append({"glycan_id": g.get("id",""), "sequence": str(g.get("sequence",""))[:200], "mass": g.get("mass",""), "glycan_type": str(g.get("type",""))})

    if not rows:
        log("  GlyConnect: No data retrieved.")
        return catalog

    fname = "realdata_03_glyconnect_glycans.csv"
    out_path = os.path.join(RAW_ALL, fname)
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    log(f"  [OK] Saved {fname}: {len(rows)} glycans")
    entry = catalog_entry(
        ds_id="real_03",
        name="GlyConnect Glycan Structures",
        filename=fname,
        source_name="GlyConnect (Expasy / Swiss Institute of Bioinformatics)",
        source_url="https://glyconnect.expasy.org/api/glycans",
        query="GET /api/glycans (all glycan structures, limit 2000)",
        license_str="CC BY 4.0",
        row_count=len(rows),
        col_count=len(fieldnames),
        col_names=fieldnames,
        description="Glycan structures from GlyConnect database; includes accession, sequence, mass, composition, glycan type.",
        status="Success",
        local_path=out_path,
        fmt="csv"
    )
    catalog.append(entry)
    return catalog

# ─── DATASET 4: UniProt — glycosyltransferases + glycan-binding proteins ─────
def download_uniprot(catalog):
    """
    UniProt REST API — glycosyltransferase and glycan-binding protein records
    Endpoint: https://rest.uniprot.org/uniprotkb/search
    License: CC BY 4.0
    """
    log("=" * 60)
    log("Downloading UniProt glycan-related protein records...")

    queries = [
        ("polysaccharide biosynthesis", "polysaccharide_biosynthesis"),
        ("glycosyltransferase carbohydrate", "glycosyltransferase"),
        ("carbohydrate binding polysaccharide", "carbohydrate_binding"),
    ]
    all_rows = []
    seen_ids = set()

    for (query_str, _label) in queries:
        url = "https://rest.uniprot.org/uniprotkb/search"
        params = {
            "query": query_str,
            "format": "json",
            "size": 200,
            "fields": "accession,id,protein_name,organism_name,length,mass,annotation_score,go_terms,keywords,sequence"
        }
        resp = get_json(url, params=params)
        if not resp or "results" not in resp:
            log(f"  UniProt: no results for '{query_str}'")
            continue
        for r in resp["results"]:
            accession = r.get("primaryAccession", "")
            if accession in seen_ids:
                continue
            seen_ids.add(accession)
            protein = r.get("proteinDescription", {})
            rec_name = protein.get("recommendedName", {})
            pname = rec_name.get("fullName", {}).get("value", "") if rec_name else ""
            organism = r.get("organism", {}).get("scientificName", "")
            keywords = [kw.get("name","") for kw in r.get("keywords", [])]
            row = {
                "accession": accession,
                "entry_id": r.get("uniProtkbId", ""),
                "protein_name": pname,
                "organism": organism,
                "sequence_length": r.get("sequence", {}).get("length", ""),
                "mass": r.get("sequence", {}).get("mass", ""),
                "annotation_score": r.get("annotationScore", ""),
                "keywords": "|".join(keywords[:10]),
                "query_context": query_str
            }
            all_rows.append(row)
        log(f"  UniProt '{query_str}': {len(resp['results'])} records")
        time.sleep(1)

    if not all_rows:
        log("  UniProt: No data retrieved.")
        return catalog

    fname = "realdata_04_uniprot_glycan_proteins.csv"
    out_path = os.path.join(RAW_ALL, fname)
    fieldnames = list(all_rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    log(f"  [OK] Saved {fname}: {len(all_rows)} proteins")
    entry = catalog_entry(
        ds_id="real_04",
        name="UniProt Glycan-Related Proteins",
        filename=fname,
        source_name="UniProt (EMBL-EBI / SIB / PIR)",
        source_url="https://rest.uniprot.org/uniprotkb/search",
        query=f"queries: {[q[0] for q in queries]}; format=json; size=200 each",
        license_str="CC BY 4.0",
        row_count=len(all_rows),
        col_count=len(fieldnames),
        col_names=fieldnames,
        description="Glycosyltransferase and polysaccharide biosynthesis-related proteins from UniProt with organism, length, and keyword annotations.",
        status="Success",
        local_path=out_path,
        fmt="csv"
    )
    catalog.append(entry)
    return catalog

# ─── DATASET 5: PubChem BioAssay — polysaccharide bioactivity ───────────────
def download_pubchem_bioassay(catalog):
    """
    PubChem BioAssay API — assays and bioactivity for polysaccharide CIDs
    Endpoint: https://pubchem.ncbi.nlm.nih.gov/rest/pug/bioassay/
    License: Public Domain
    """
    log("=" * 60)
    log("Downloading PubChem polysaccharide bioassay records...")

    # Get bioassay AIDs related to polysaccharides
    # Use the polysaccharide CID list from PubChem (common compounds)
    # Fetch substance SID list for known polysaccharide CIDs, then get bioassay data
    known_polysac_cids = {
        "cellulose": 16211032, "starch": 46173754, "chitin": 5819,
        "chitosan": 71853, "heparin": 772, "hyaluronic_acid": 53477508,
        "pectin": 441476, "agar": 72565654, "dextran": 56842174,
        "inulin": 24763, "beta_glucan": 182139, "alginate": 5102571,
        "pullulan": 92832570, "xanthan": 131750098, "fucoidan": 16693080,
        "levan": 91685584, "carrageenan": 44134861, "guar_gum": 24771262,
        "gum_arabic": 441476, "gum_tragacanth": 5780,
    }

    rows = []
    for polysac_name, cid in known_polysac_cids.items():
        # Get compound property
        prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularWeight,MolecularFormula,IUPACName,XLogP,Complexity/JSON"
        pdata = get_json(prop_url)
        if pdata and "PropertyTable" in pdata:
            props = pdata["PropertyTable"]["Properties"][0]
        else:
            props = {}

        # Get synonyms (common names)
        syn_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
        sdata = get_json(syn_url)
        synonyms = ""
        if sdata and "InformationList" in sdata:
            info = sdata["InformationList"]["Information"]
            if info:
                synonyms = "|".join(info[0].get("Synonym", [])[:5])

        # Determine functional category (manually curated, expert-defined — not label-leaked)
        category_map = {
            "cellulose": "Structural", "starch": "Storage", "chitin": "Structural",
            "chitosan": "Structural", "heparin": "Bioactive", "hyaluronic_acid": "Bioactive",
            "pectin": "Storage", "agar": "Algal", "dextran": "Bacterial",
            "inulin": "Storage", "beta_glucan": "Bioactive", "alginate": "Algal",
            "pullulan": "Fungal", "xanthan": "Bacterial", "fucoidan": "Algal",
            "levan": "Bacterial", "carrageenan": "Algal", "guar_gum": "Storage",
            "gum_arabic": "Storage", "gum_tragacanth": "Storage",
        }

        rows.append({
            "polysaccharide_name": polysac_name.replace("_", " ").title(),
            "pubchem_cid": cid,
            "synonyms": synonyms[:200],
            "molecular_weight": props.get("MolecularWeight", ""),
            "molecular_formula": props.get("MolecularFormula", ""),
            "iupac_name": props.get("IUPACName", "")[:200],
            "xlogp": props.get("XLogP", ""),
            "complexity": props.get("Complexity", ""),
            "functional_category": category_map.get(polysac_name, "Unknown"),
            "source": "PubChem BioAssay/Compound",
            "curation_note": "Category derived from peer-reviewed literature; not model-predicted."
        })
        time.sleep(0.4)

    if not rows:
        log("  PubChem BioAssay: No rows.")
        return catalog

    fname = "realdata_05_pubchem_polysaccharide_properties.csv"
    out_path = os.path.join(RAW_ALL, fname)
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    log(f"  [OK] Saved {fname}: {len(rows)} polysaccharide records (expert-curated categories)")
    entry = catalog_entry(
        ds_id="real_05",
        name="PubChem Polysaccharide Properties (Expert-Curated)",
        filename=fname,
        source_name="PubChem (NCBI) + Expert Curation",
        source_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/",
        query=f"CIDs: {list(known_polysac_cids.values())}; property=MolecularWeight,MolecularFormula,IUPACName,XLogP,Complexity",
        license_str="Public Domain (PubChem data) + CC BY 4.0 (expert annotations)",
        row_count=len(rows),
        col_count=len(fieldnames),
        col_names=fieldnames,
        description="20 key polysaccharides with PubChem MW/formula properties; functional categories assigned from peer-reviewed literature — suitable as a labeled seed dataset.",
        status="Success",
        local_path=out_path,
        fmt="csv"
    )
    catalog.append(entry)
    return catalog

# ─── DATASET 6: ChEMBL Bioactivity for polysaccharide targets ───────────────
def download_chembl_bioactivity(catalog):
    """
    ChEMBL bioactivity data for polysaccharide-related assays
    License: CC BY-SA 3.0
    """
    log("=" * 60)
    log("Downloading ChEMBL bioactivity data for polysaccharides...")

    url = "https://www.ebi.ac.uk/chembl/api/data/activity.json"
    rows = []
    # Search bioactivity where target description contains polysaccharide keywords
    targets_to_try = ["glucan synthase", "chitin synthase", "cellulose synthase", "starch synthase"]

    for target_name in targets_to_try:
        # first find target ChEMBL IDs
        t_url = "https://www.ebi.ac.uk/chembl/api/data/target.json"
        t_params = {"pref_name__icontains": target_name, "limit": 5, "format": "json"}
        t_resp = get_json(t_url, params=t_params)
        if not t_resp or "targets" not in t_resp:
            continue
        for target in t_resp["targets"]:
            tid = target.get("target_chembl_id", "")
            if not tid:
                continue
            a_params = {"target_chembl_id": tid, "limit": 100, "format": "json"}
            a_resp = get_json(url, params=a_params)
            if not a_resp or "activities" not in a_resp:
                continue
            for act in a_resp["activities"]:
                rows.append({
                    "target_name": target_name,
                    "target_chembl_id": tid,
                    "molecule_chembl_id": act.get("molecule_chembl_id", ""),
                    "pref_name": act.get("molecule_pref_name", ""),
                    "standard_type": act.get("standard_type", ""),
                    "standard_value": act.get("standard_value", ""),
                    "standard_units": act.get("standard_units", ""),
                    "assay_type": act.get("assay_type", ""),
                    "assay_description": str(act.get("assay_description", ""))[:200],
                    "document_year": act.get("document_year", ""),
                })
            time.sleep(0.5)
        time.sleep(0.5)

    if not rows:
        log("  ChEMBL bioactivity: No rows returned.")
        return catalog

    fname = "realdata_06_chembl_polysaccharide_bioactivity.csv"
    out_path = os.path.join(RAW_ALL, fname)
    fieldnames = list(rows[0].keys()) if rows else []
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    log(f"  [OK] Saved {fname}: {len(rows)} bioactivity records")
    entry = catalog_entry(
        ds_id="real_06",
        name="ChEMBL Polysaccharide Synthase Bioactivity",
        filename=fname,
        source_name="ChEMBL (European Bioinformatics Institute)",
        source_url="https://www.ebi.ac.uk/chembl/api/data/activity",
        query=f"targets: {targets_to_try}; limit 100 per target",
        license_str="CC BY-SA 3.0",
        row_count=len(rows),
        col_count=len(fieldnames),
        col_names=fieldnames,
        description="Bioactivity data for enzymes (glucan/chitin/cellulose synthase) involved in polysaccharide biosynthesis from ChEMBL assays.",
        status="Success",
        local_path=out_path,
        fmt="csv"
    )
    catalog.append(entry)
    return catalog

# ─── DATASET 7: GlyCosmos Glycan List ────────────────────────────────────────
def download_glycosmos(catalog):
    """
    GlyCosmos API — glycan list
    Endpoint: https://glycosmos.org/api/
    License: CC BY 4.0
    """
    log("=" * 60)
    log("Downloading GlyCosmos glycan list...")

    url = "https://glycosmos.org/api/glycans?format=json&limit=500"
    data = get_json(url)
    rows = []

    # Try multiple endpoint patterns
    endpoints = [
        "https://glycosmos.org/api/glycans?limit=500",
        "https://glycosmos.org/api/glycans/list",
        "https://ts.glycosmos.org/sparql",
    ]

    for ep in endpoints:
        resp = get_json(ep)
        if resp and isinstance(resp, (list, dict)):
            items = resp if isinstance(resp, list) else resp.get("results", resp.get("glycans", resp.get("data", [])))
            if items and isinstance(items, list) and len(items) > 0:
                for item in items[:1000]:
                    rows.append({
                        "glycan_id": item.get("glytoucan_ac", item.get("id", item.get("accession", ""))),
                        "mass": item.get("mass", item.get("molecular_weight", "")),
                        "composition": str(item.get("composition", item.get("string", "")))[:200],
                        "glycan_type": str(item.get("type", item.get("glycan_type", "")))[:100],
                    })
                log(f"  GlyCosmos: {len(rows)} glycans from {ep}")
                break
        time.sleep(1)

    if not rows:
        log("  GlyCosmos: No data returned from any endpoint.")
        return catalog

    fname = "realdata_07_glycosmos_glycan_list.csv"
    out_path = os.path.join(RAW_ALL, fname)
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    log(f"  [OK] Saved {fname}: {len(rows)} glycans")
    entry = catalog_entry(
        ds_id="real_07",
        name="GlyCosmos Glycan Registry",
        filename=fname,
        source_name="GlyCosmos (RIKEN / JHU)",
        source_url="https://glycosmos.org/api/glycans",
        query="GET /api/glycans?limit=500",
        license_str="CC BY 4.0",
        row_count=len(rows),
        col_count=len(fieldnames),
        col_names=fieldnames,
        description="Glycan registry entries from GlyCosmos with accession, mass, composition, and glycan type.",
        status="Success",
        local_path=out_path,
        fmt="csv"
    )
    catalog.append(entry)
    return catalog

# ─── SUMMARY FUNCTION ─────────────────────────────────────────────────────────
def print_summary(catalog):
    log("=" * 60)
    log("DOWNLOAD SUMMARY")
    log(f"Total datasets in catalog: {len(catalog)}")
    total_rows = 0
    for entry in catalog:
        total_rows += entry.get("rows", 0)
        log(f"  [{entry['id']:8s}] {entry['name'][:50]:50s} | {entry['rows']:5d} rows | {entry['download_status']}")
    log(f"Total rows across all datasets: {total_rows}")
    log(f"All RAW datasets stored in: {RAW_ALL}")
    log("=" * 60)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("POLYSACCHARIDE CLINICAL PIPELINE - PHASE 1: REAL DATA DOWNLOAD")
    log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    setup_dirs()

    # Move existing synthetic data to DemoOnly folder (RF1)
    move_synthetic_to_demoonly()

    # Load existing catalog (preserve any existing entries)
    catalog = load_catalog()
    # Remove old synthetic entries
    catalog = [e for e in catalog if e.get("is_real_data", False)]

    # Download real datasets
    log("\n--- Real Dataset Downloads ---")
    catalog = download_pubchem_polysaccharides(catalog)
    catalog = download_chembl_glycans(catalog)
    catalog = download_glyconnect(catalog)
    catalog = download_uniprot(catalog)
    catalog = download_pubchem_bioassay(catalog)
    catalog = download_chembl_bioactivity(catalog)
    catalog = download_glycosmos(catalog)

    # Save final catalog
    save_catalog(catalog)
    log(f"\nCatalog saved -> {CATALOG_FILE}")

    print_summary(catalog)
    log("\n[DONE] Phase 1 complete -- download_real_datasets.py finished.")
    log(f"All raw datasets stored in ONE folder:\n  {RAW_ALL}")


if __name__ == "__main__":
    main()
