"""FAISS-based similarity search with scikit-learn fallback."""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, Optional
from sklearn.preprocessing import StandardScaler
from shared.ml.config import FEATURE_COLUMNS

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

class FAISSSearchEngine:
    def __init__(self):
        self.scaler: Optional[StandardScaler] = None
        self.index = None
        self.fallback_nn = None
        self.feature_matrix: Optional[np.ndarray] = None

    def build_index(self, df: pd.DataFrame, scaler: StandardScaler = None):
        X = df[FEATURE_COLUMNS].values.astype(np.float32)
        if scaler is None:
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X).astype(np.float32)
        else:
            self.scaler = scaler
            X_scaled = self.scaler.transform(X).astype(np.float32)

        self.feature_matrix = X_scaled

        if HAS_FAISS:
            d = X_scaled.shape[1]
            self.index = faiss.IndexFlatL2(d)
            self.index.add(X_scaled)
        else:
            from sklearn.neighbors import NearestNeighbors
            n_samples = max(1, len(X_scaled))
            self.fallback_nn = NearestNeighbors(n_neighbors=min(10, n_samples), metric="euclidean")
            self.fallback_nn.fit(X_scaled)

    def search(self, query_features: Dict[str, float], k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        if self.feature_matrix is None:
            raise RuntimeError("FAISS index not built. Call build_index() first.")

        q_vec = np.array([[query_features.get(c, 0.0) for c in FEATURE_COLUMNS]], dtype=np.float32)
        q_scaled = self.scaler.transform(q_vec).astype(np.float32)
        k = min(k, self.feature_matrix.shape[0])

        if HAS_FAISS and self.index is not None:
            distances, indices = self.index.search(q_scaled, k)
            return indices[0], distances[0]
        elif self.fallback_nn is not None:
            distances, indices = self.fallback_nn.kneighbors(q_scaled, n_neighbors=k)
            return indices[0], distances[0]
        else:
            return np.array([0]), np.array([0.0])

    def search_dataframe(self, df: pd.DataFrame, query_features: Dict[str, float], k: int = 10) -> pd.DataFrame:
        indices, distances = self.search(query_features, k=k)
        result = df.iloc[indices].copy()
        result["similarity_distance"] = distances
        return result
