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
