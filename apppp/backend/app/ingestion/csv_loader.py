"""CSV loader and row parser for dataset ingestion."""

from typing import Dict, Any, Tuple

def parse_csv_row(row: Dict[str, str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Parse a raw CSV dictionary row into material metadata and typed properties."""
    mat_data = {
        "name": row.get("name", "").strip(),
        "category": row.get("category", "").strip(),
        "source": row.get("source", "").strip(),
        "evidence_level": row.get("evidence_level", "").strip(),
        "notes": row.get("notes", "").strip(),
        "references": row.get("references", "").strip(),
    }

    prop_data: Dict[str, Any] = {}
    for key, val in row.items():
        if key in mat_data:
            continue
        if val is None or val.strip() == "":
            prop_data[key] = None
        else:
            val_clean = val.strip()
            if val_clean.lower() == "true":
                prop_data[key] = True
            elif val_clean.lower() == "false":
                prop_data[key] = False
            else:
                try:
                    if "." in val_clean:
                        prop_data[key] = float(val_clean)
                    else:
                        prop_data[key] = int(val_clean)
                except ValueError:
                    prop_data[key] = val_clean

    return mat_data, prop_data
