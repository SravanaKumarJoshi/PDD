"""
Performance & latency tracking for each pipeline stage.
Target: total response < 1 second.
"""
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineTimer:
    """Tracks timing for each pipeline stage."""
    stages: dict[str, float] = field(default_factory=dict)
    _start_times: dict[str, float] = field(default_factory=dict)
    _pipeline_start: float = 0.0

    def start_pipeline(self):
        self._pipeline_start = time.perf_counter()

    def start_stage(self, name: str):
        self._start_times[name] = time.perf_counter()

    def end_stage(self, name: str):
        if name in self._start_times:
            elapsed = (time.perf_counter() - self._start_times[name]) * 1000
            self.stages[name] = round(elapsed, 2)

    @property
    def total_ms(self) -> float:
        if self._pipeline_start:
            return round((time.perf_counter() - self._pipeline_start) * 1000, 2)
        return sum(self.stages.values())

    @property
    def meets_target(self) -> bool:
        return self.total_ms < 1000

    def get_report(self) -> dict[str, Any]:
        total = self.total_ms
        return {
            "stages": dict(self.stages),
            "total_ms": total,
            "meets_1s_target": total < 1000,
            "slowest_stage": (
                max(self.stages, key=self.stages.get)
                if self.stages else "N/A"
            ),
        }

    def format_report(self) -> str:
        """Human-readable latency report."""
        lines = ["**Pipeline Latency:**"]
        for name, ms in self.stages.items():
            bar_len = int(ms / 10)
            bar = "█" * min(bar_len, 50)
            lines.append(f"  {name}: {ms:.1f}ms {bar}")
        total = self.total_ms
        status = "✅" if total < 1000 else "⚠️"
        lines.append(f"  **Total: {total:.1f}ms** {status}")
        return "\n".join(lines)
