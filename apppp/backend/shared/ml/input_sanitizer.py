"""Input sanitization layer — strips malicious vectors and enforces schema types."""

import html
import re
from typing import Dict, Any

def sanitize_string(value: str) -> str:
    """Strip HTML tags, SQL injection characters, and sanitize strings."""
    if not isinstance(value, str):
        return ""
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]*>", "", value)
    # Escape special characters
    cleaned = html.escape(cleaned)
    # Strip dangerous characters
    cleaned = re.sub(r"[;'\"--]", "", cleaned)
    return cleaned.strip()

def sanitize_screening_request(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize all input fields in a screening request."""
    sanitized = {}
    for k, v in input_dict.items():
        clean_key = sanitize_string(k)
        if isinstance(v, str):
            sanitized[clean_key] = sanitize_string(v)
        elif isinstance(v, (int, float, bool)):
            sanitized[clean_key] = v
        elif isinstance(v, dict):
            sanitized[clean_key] = sanitize_screening_request(v)
        elif isinstance(v, list):
            sanitized[clean_key] = [
                sanitize_string(item) if isinstance(item, str) else item
                for item in v
            ]
        else:
            # Drop unhandled types
            pass
    return sanitized

def has_valid_screening_criteria(input_dict: Dict[str, Any]) -> bool:
    """Check whether a screening request contains at least one non-empty, valid criterion."""
    if not isinstance(input_dict, dict) or not input_dict:
        return False

    # Ignore meta/config keys that are not user screening criteria
    ignored_keys = {"explainability_method", "weight_mechanical", "weight_barrier", "weight_biological", "weight_degradation"}

    for key, val in input_dict.items():
        if key in ignored_keys:
            continue
        if val is None:
            continue
        if isinstance(val, str) and val.strip() != "":
            return True
        if isinstance(val, (int, float)) and val > 0:
            return True
        if isinstance(val, bool) and val is True:
            return True
        if isinstance(val, dict) and has_valid_screening_criteria(val):
            return True
        if isinstance(val, list) and len(val) > 0:
            return True

    return False

