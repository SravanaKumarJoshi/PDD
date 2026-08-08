"""MonitoringService: Continuous AI model behaviour, feature drift, and latency tracker."""

import time
import logging
from typing import Dict, List, Any
import numpy as np

logger = logging.getLogger(__name__)

class MonitoringService:
    """Collects runtime telemetry on predictions, latency, confidence, and feature distributions."""

    _total_requests = 0
    _total_errors = 0
    _cache_hits = 0
    _cache_misses = 0
    _latencies_ms: List[float] = []
    _confidences: List[float] = []
    _predictions: List[float] = []

    @classmethod
    def record_inference(
        cls,
        total_duration_ms: float,
        confidence_scores: List[float],
        predictions: List[float],
        cache_hit: bool = False,
    ):
        cls._total_requests += 1
        if cache_hit:
            cls._cache_hits += 1
        else:
            cls._cache_misses += 1

        cls._latencies_ms.append(total_duration_ms)
        cls._confidences.extend(confidence_scores)
        cls._predictions.extend(predictions)

        # Keep rolling window of last 1000 requests
        if len(cls._latencies_ms) > 1000:
            cls._latencies_ms = cls._latencies_ms[-1000:]
        if len(cls._confidences) > 1000:
            cls._confidences = cls._confidences[-1000:]
        if len(cls._predictions) > 1000:
            cls._predictions = cls._predictions[-1000:]

    @classmethod
    def record_error(cls):
        cls._total_errors += 1

    @classmethod
    def get_metrics_summary(cls) -> Dict[str, Any]:
        avg_latency = float(np.mean(cls._latencies_ms)) if cls._latencies_ms else 0.0
        p95_latency = float(np.percentile(cls._latencies_ms, 95)) if cls._latencies_ms else 0.0
        avg_confidence = float(np.mean(cls._confidences)) if cls._confidences else 0.0
        hit_ratio = float(cls._cache_hits / cls._total_requests) if cls._total_requests > 0 else 0.0

        return {
            "total_requests": cls._total_requests,
            "total_errors": cls._total_errors,
            "cache_hits": cls._cache_hits,
            "cache_misses": cls._cache_misses,
            "cache_hit_ratio": round(hit_ratio, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "avg_confidence": round(avg_confidence, 4),
            "model_drift_warning": False if avg_confidence > 0.4 else True,
        }
