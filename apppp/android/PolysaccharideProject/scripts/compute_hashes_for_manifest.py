import hashlib
import os
import json

BASE_DIR = "D:/Sravan/PDD/apppp/android/PolysaccharideProject"
DATASET_PATH = os.path.join(BASE_DIR, "datasets/processed/master_clinical_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models/clinical/clinical_model_pipeline.joblib")
MANIFEST_PATH = os.path.join(BASE_DIR, "models/clinical/model_manifest.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "reports/audit_hashes.json")

def get_sha256(p):
    if not os.path.exists(p): return None
    s = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(4096), b""):
            s.update(b)
    return s.hexdigest()

d_sha = get_sha256(DATASET_PATH)
m_sha = get_sha256(MODEL_PATH)

results = {
    "dataset_sha256": d_sha,
    "model_pipeline_sha256": m_sha
}

with open(OUTPUT_PATH, "w") as f:
    json.dump(results, f, indent=4)

if os.path.exists(MANIFEST_PATH):
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    manifest["dataset_sha256"] = d_sha
    manifest["model_pipeline_sha256"] = m_sha
    if "dataset_hash_md5" in manifest:
        manifest["dataset_hash_md5_deprecated"] = True

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=4)
