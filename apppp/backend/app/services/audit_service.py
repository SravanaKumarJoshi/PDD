"""Audit Service.

Persists screening session audit records to logs/audit/ for reproducibility,
versioning, and historical auditing.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
AUDIT_LOG_DIR = ROOT_DIR / "logs" / "audit"


class AuditService:
    """Manages audit logging and session persistence for screening requests."""

    @classmethod
    def record_screening_session(
        cls,
        session_id: str,
        request_data: Dict[str, Any],
        audit_metadata: Dict[str, Any],
        results_summary: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        validation_diagnostics: Dict[str, Any],
    ) -> bool:
        """Persist structured audit record to disk."""
        try:
            AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_file = AUDIT_LOG_DIR / f"trace_{session_id}.json"

            audit_payload = {
                "screening_session_id": session_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "audit_metadata": audit_metadata,
                "request_data": request_data,
                "results_summary": results_summary,
                "performance": performance_metrics,
                "validation": validation_diagnostics,
            }

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(audit_payload, f, indent=2, default=str)

            logger.info(f"Screening audit record saved: trace_{session_id}.json")
            return True
        except Exception as e:
            logger.error(f"Failed to save audit record for session {session_id}: {e}")
            return False
