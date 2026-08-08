"""
FAISS-based similarity search for production-scale material matching.
Falls back to scikit-learn NearestNeighbors if FAISS unavailable.
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from typing import Optional

from src.data import FEATURE_COLUMNS

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

# Module-level state
_scaler: Optional[StandardScaler] = None
_index = None
_feature_matrix: Optional[np.ndarray] = None
_fallback_nn = None


def build_index(df: pd.DataFrame, feature_cols: list[str] = None):
    """Build FAISS index (or sklearn fallback) from dataset."""
    global _scaler, _index, _feature_matrix, _fallback_nn

    feature_cols = feature_cols or FEATURE_COLUMNS
    X = df[feature_cols].values.astype(np.float32)

    _scaler = StandardScaler()
    X_scaled = _scaler.fit_transform(X).astype(np.float32)
    _feature_matrix = X_scaled

    if HAS_FAISS:
        d = X_scaled.shape[1]
        _index = faiss.IndexFlatL2(d)
        _index.add(X_scaled)
    else:
        from sklearn.neighbors import NearestNeighbors
        _fallback_nn = NearestNeighbors(n_neighbors=min(10, len(X)), metric="euclidean")
        _fallback_nn.fit(X_scaled)


def find_similar(
    query_features: dict | np.ndarray,
    k: int = 10,
    feature_cols: list[str] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Find k most similar materials to query.
    Returns (indices, distances).
    """
    feature_cols = feature_cols or FEATURE_COLUMNS

    if isinstance(query_features, dict):
        q = np.array([[query_features.get(c, 0.0) for c in feature_cols]], dtype=np.float32)
    else:
        q = np.array(query_features, dtype=np.float32).reshape(1, -1)

    q_scaled = _scaler.transform(q).astype(np.float32)
    k = min(k, _feature_matrix.shape[0])

    if HAS_FAISS and _index is not None:
        distances, indices = _index.search(q_scaled, k)
        return indices[0], distances[0]
    elif _fallback_nn is not None:
        distances, indices = _fallback_nn.kneighbors(q_scaled, n_neighbors=k)
        return indices[0], distances[0]
    else:
        raise RuntimeError("No similarity index built. Call build_index() first.")


def find_similar_materials(
    df: pd.DataFrame,
    query_features: dict,
    k: int = 10,
    feature_cols: list[str] = None,
) -> pd.DataFrame:
    """
    Convenience: returns a DataFrame of the k most similar materials.
    """
    indices, distances = find_similar(query_features, k, feature_cols)
    result = df.iloc[indices].copy()
    result["similarity_distance"] = distances
    result["similarity_rank"] = range(1, len(indices) + 1)
    return result
