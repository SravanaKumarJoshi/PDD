import hashlib
import os
import json

BASE_DIR = "D:/Sravan/PDD/apppp/android/PolysaccharideProject"
MASTER_DATA = os.path.join(BASE_DIR, "datasets/processed/master_clinical_dataset.csv")
MODEL_PIPELINE = os.path.join(BASE_DIR, "models/clinical/clinical_model_pipeline.joblib")
MANIFEST_FILE = os.path.join(BASE_DIR, "models/clinical/model_manifest.json")

def get_sha256(filepath):
    if not os.path.exists(filepath):
        return None
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def update_manifest():
    data_sha = get_sha256(MASTER_DATA)
    model_sha = get_sha256(MODEL_PIPELINE)

    print(f"Dataset SHA256: {data_sha}")
    print(f"Model SHA256: {model_sha}")

    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r") as f:
            manifest = json.load(f)

        # Add new hashes
        manifest["dataset_sha256"] = data_sha
        manifest["model_pipeline_sha256"] = model_sha

        # Deprecate MD5
        if "dataset_hash_md5" in manifest:
            manifest["dataset_hash_md5_deprecated"] = True

        with open(MANIFEST_FILE, "w") as f:
            json.dump(manifest, f, indent=4)
        print("Manifest updated.")

if __name__ == "__main__":
    update_manifest()
