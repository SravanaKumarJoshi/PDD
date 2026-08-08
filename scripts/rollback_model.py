#!/usr/bin/env python3
"""
rollback_model.py — Immediate Model Rollback CLI Tool with Deployment Audit Trail

Rolls back the active 'latest' model pointer to a specified previous version
and records an immutable deployment entry in deployment_audit_log.jsonl.
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT_DIR / "models" / "registry"

def record_deployment_audit_log(action: str, prev_version: str, new_version: str, performed_by: str, reason: str):
    log_file = REGISTRY_DIR / "deployment_audit_log.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "previous_version": prev_version,
        "new_version": new_version,
        "performed_by": performed_by,
        "reason": reason
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def rollback(target_version: str, performed_by: str = "admin_cli", reason: str = "Manual operational rollback"):
    target_dir = REGISTRY_DIR / target_version
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: Target model version '{target_version}' does not exist in {REGISTRY_DIR}.", file=sys.stderr)
        sys.exit(1)

    latest_pointer = REGISTRY_DIR / "latest"
    prev_version = "unknown"

    if latest_pointer.exists():
        try:
            target_resolved = latest_pointer.resolve() if latest_pointer.is_symlink() else latest_pointer
            meta_prev = target_resolved / "metadata.json"
            if meta_prev.exists():
                with open(meta_prev, "r", encoding="utf-8") as pf:
                    prev_version = json.load(pf).get("model_version", "unknown")
        except Exception:
            pass

    # Remove existing symlink or copy
    if latest_pointer.exists() or latest_pointer.is_symlink():
        if latest_pointer.is_symlink() or os.name != "nt":
            latest_pointer.unlink()
        else:
            shutil.rmtree(latest_pointer)

    try:
        latest_pointer.symlink_to(target_dir, target_is_directory=True)
        print(f"Successfully symlinked 'latest' -> {target_version}")
    except Exception:
        shutil.copytree(target_dir, latest_pointer)
        print(f"Successfully copied '{target_version}' -> 'latest'")

    # Record audit log
    record_deployment_audit_log(
        action="ROLLBACK",
        prev_version=prev_version,
        new_version=target_version,
        performed_by=performed_by,
        reason=reason
    )

def main():
    parser = argparse.ArgumentParser(description="BioPolymer Model Rollback Tool")
    parser.add_argument("--target", required=True, help="Target model version (e.g. v1, v2)")
    parser.add_argument("--user", default="admin_cli", help="User performing rollback")
    parser.add_argument("--reason", default="Manual rollback trigger", help="Reason for rollback")
    args = parser.parse_args()

    print(f"Initiating rollback to version '{args.target}'...")
    rollback(args.target, performed_by=args.user, reason=args.reason)

if __name__ == "__main__":
    main()
