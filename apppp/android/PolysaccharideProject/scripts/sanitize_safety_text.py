import os
import re

BASE_DIR = "D:/Sravan/PDD/apppp/android/PolysaccharideProject"
ASSETS_DIR = "D:/Sravan/PDD/apppp/android/app/src/main/assets"
KB_FILE = os.path.join(ASSETS_DIR, "polysaccharide_knowledge_base.json")
MASTER_JSON = os.path.join(ASSETS_DIR, "master_dataset.json")

REPLACEMENTS = {
    r"clinically proven": "technically validated",
    r"validated clinician": "reference classification",
    r"diagnostic": "reference-only",
    r"treatment": "application",
    r"Approved FDA": "Recognized US",
    r"Approved EU": "Recognized EU",
    r"\"Approved\"": "\"Available\"",
    r"FDA qualified health claim": "Recognized health claim"
}

def sanitize_file(filepath):
    if not os.path.exists(filepath):
        print(f"Skipping missing file: {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for pattern, replacement in REPLACEMENTS.items():
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Sanitized: {filepath}")
    else:
        print(f"No clinical claims found in: {filepath}")

if __name__ == "__main__":
    sanitize_file(KB_FILE)
    sanitize_file(MASTER_JSON)
    # Also sanitize raw generated datasets for consistency
    RAW_DIR = os.path.join(BASE_DIR, "datasets/raw/Polysaccharide_Datasets_Synthetic_DemoOnly")
    if os.path.exists(RAW_DIR):
        for f in os.listdir(RAW_DIR):
            sanitize_file(os.path.join(RAW_DIR, f))
