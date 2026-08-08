import hashlib
import os

files = [
    "D:/Sravan/PDD/apppp/android/PolysaccharideProject/datasets/processed/master_clinical_dataset.csv",
    "D:/Sravan/PDD/apppp/android/PolysaccharideProject/models/clinical/clinical_model_pipeline.joblib"
]

for f in files:
    if os.path.exists(f):
        sha256_hash = hashlib.sha256()
        with open(f, "rb") as fh:
            for byte_block in iter(lambda: fh.read(4096), b""):
                sha256_hash.update(byte_block)
        print(f"{os.path.basename(f)} SHA256: {sha256_hash.hexdigest()}")
    else:
        print(f"{os.path.basename(f)}: NOT FOUND")
