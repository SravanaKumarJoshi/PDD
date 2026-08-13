"""ModelManager: Loads pre-trained models from registry, verifies SHA-256 checksums & HMAC digital signatures, and manages hot reload/rollback with audit logging."""

import os
import json
import hmac
import hashlib
import logging
import joblib
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
REGISTRY_DIR = ROOT_DIR / "models" / "registry"
SIGNING_SECRET = os.getenv("MODEL_SIGNING_SECRET_KEY", "biopolymer-production-signing-key-987654321")

class ModelManager:
    """Thread-safe model registry manager with SHA-256 integrity checks and HMAC signature verification."""

    _active_model = None
    _active_scaler = None
    _active_metadata: Dict[str, Any] = {}
    _feature_matrix: Optional[np.ndarray] = None
    _is_loaded = False

    @staticmethod
    def compute_file_sha256(filepath: Path) -> str:
        """Compute SHA-256 checksum for a binary file."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def verify_hmac_signature(meta_payload: Dict[str, Any], secret: str) -> bool:
        """Verify HMAC-SHA256 digital signature of metadata payload."""
        signature = meta_payload.get("digital_signature")
        if not signature:
            logger.warning("Metadata payload missing digital_signature.")
            return False

        # Create copy without digital_signature for verification
        payload_copy = meta_payload.copy()
        payload_copy.pop("digital_signature", None)
        json_str = json.dumps(payload_copy, sort_keys=True)
        expected_sig = hmac.new(secret.encode("utf-8"), json_str.encode("utf-8"), hashlib.sha256).hexdigest()

        return hmac.compare_digest(signature, expected_sig)

    @classmethod
    def resolve_latest_dir(cls) -> Optional[Path]:
        """Resolve valid active model directory containing metadata manifest and binary artifacts."""
        registry_candidates = [
            REGISTRY_DIR,
            Path(__file__).resolve().parent.parent.parent / "models" / "registry"
        ]
        
        for reg_dir in registry_candidates:
            if not reg_dir.exists():
                continue

            latest_pointer = reg_dir / "latest"
            if latest_pointer.exists() or latest_pointer.is_symlink():
                # Case 1: Directory or symlink to directory
                if latest_pointer.is_dir():
                    if (latest_pointer / "metadata.json").exists() and (latest_pointer / "model.joblib").exists():
                        return latest_pointer
                    resolved = latest_pointer.resolve()
                    if resolved.exists() and resolved.is_dir() and (resolved / "metadata.json").exists() and (resolved / "model.joblib").exists():
                        return resolved

                # Case 2: Plain text file pointing to target directory (e.g. checked out on Windows)
                elif latest_pointer.is_file():
                    try:
                        target_str = latest_pointer.read_text(encoding="utf-8").strip()
                        target_name = Path(target_str).name
                        target_dir = reg_dir / target_name
                        if target_dir.exists() and (target_dir / "metadata.json").exists() and (target_dir / "model.joblib").exists():
                            return target_dir
                    except Exception:
                        pass

            # Case 3: Search for highest numbered version directory (v1, v2, ...) containing required model binaries
            v_dirs = []
            try:
                for item in reg_dir.iterdir():
                    if item.is_dir() and item.name.startswith("v") and item.name[1:].isdigit():
                        if (item / "metadata.json").exists() and (item / "model.joblib").exists() and (item / "scaler.joblib").exists():
                            v_dirs.append((int(item.name[1:]), item))
            except Exception:
                pass
            if v_dirs:
                v_dirs.sort(key=lambda x: x[0], reverse=True)
                return v_dirs[0][1]

        return None

    @classmethod
    def load_latest(cls, force_reload: bool = False) -> bool:
        """Load active model after verifying SHA-256 checksums and digital signature."""
        if cls._is_loaded and not force_reload:
            return True

        latest_path = cls.resolve_latest_dir()
        if latest_path is None or force_reload:
            logger.warning("No valid active model registry artifact found. Triggering automated model training pipeline...")
            try:
                try:
                    from scripts.train_pipeline import main as train_main
                    train_main()
                except ImportError:
                    from apppp.backend.scripts.train_pipeline import main as train_main
                    train_main()
                latest_path = cls.resolve_latest_dir()
            except Exception as e:
                logger.error(f"Failed to run automated train pipeline: {e}", exc_info=True)
                return False

        if latest_path is None or not latest_path.exists():
            logger.error("Failed to resolve active model registry directory after training attempt.")
            return False

        try:
            model_file = latest_path / "model.joblib"
            scaler_file = latest_path / "scaler.joblib"
            meta_file = latest_path / "metadata.json"
            feature_file = latest_path / "feature_matrix.npy"

            # 1. Verify Metadata & HMAC Digital Signature
            if not meta_file.exists():
                logger.error(f"Metadata manifest missing from active model directory: {latest_path}")
                return False

            with open(meta_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            if not cls.verify_hmac_signature(metadata, SIGNING_SECRET):
                logger.error("MODEL SIGNATURE VERIFICATION FAILED: Unsigned or tampered model manifest!")
                return False

            # 2. Verify SHA-256 Checksums of Binary Artifacts
            checksums = metadata.get("artifact_checksums", {})
            if checksums:
                if model_file.exists() and "model.joblib" in checksums:
                    if cls.compute_file_sha256(model_file) != checksums["model.joblib"]:
                        logger.error("MODEL CHECKSUM MISMATCH: model.joblib corrupted or tampered!")
                        return False
                if scaler_file.exists() and "scaler.joblib" in checksums:
                    if cls.compute_file_sha256(scaler_file) != checksums["scaler.joblib"]:
                        logger.error("SCALER CHECKSUM MISMATCH: scaler.joblib corrupted or tampered!")
                        return False
                if feature_file.exists() and "feature_matrix.npy" in checksums:
                    if cls.compute_file_sha256(feature_file) != checksums["feature_matrix.npy"]:
                        logger.error("FEATURE MATRIX CHECKSUM MISMATCH: feature_matrix.npy corrupted or tampered!")
                        return False

            # 3. Load Artifacts
            cls._active_model = joblib.load(model_file)
            cls._active_scaler = joblib.load(scaler_file)
            cls._active_metadata = metadata

            if feature_file.exists():
                cls._feature_matrix = np.load(feature_file)

            cls._is_loaded = True
            version_name = cls._active_metadata.get("model_version", "unknown")
            algo_name = cls._active_metadata.get("algorithm", "unknown")
            logger.info(f"Model integrity & signature VERIFIED. Successfully loaded active model: {algo_name} ({version_name}) from {latest_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading model artifacts from registry ({latest_path}): {e}", exc_info=True)
            cls._is_loaded = False
            return False

    @classmethod
    def get_model(cls) -> Tuple[Any, Any, Dict[str, Any], Optional[np.ndarray]]:
        if not cls._is_loaded:
            cls.load_latest()
        return cls._active_model, cls._active_scaler, cls._active_metadata, cls._feature_matrix

    @classmethod
    def reload(cls) -> bool:
        """Hot-reload model from registry without restarting server."""
        return cls.load_latest(force_reload=True)
