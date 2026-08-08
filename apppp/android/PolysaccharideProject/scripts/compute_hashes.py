import hashlib
import os

def get_sha256(filepath):
    if not os.path.exists(filepath):
        return None
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

dataset_path = "D:/Sravan/PDD/apppp/android/PolysaccharideProject/datasets/processed/master_clinical_dataset.csv"
model_path = "D:/Sravan/PDD/apppp/android/PolysaccharideProject/models/clinical/clinical_model_pipeline.joblib"

print(f"DATASET_SHA256: {get_sha256(dataset_path)}")
print(f"MODEL_SHA256: {get_sha256(model_path)}")
