from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_detection_count: int
    cleaned_detection_count: int
    rejected_detection_count: int
    interpolated_detection_count: int
    false_positive_delta: int


class EvaluationRunner:
    def evaluate(self, run_root: Path, _: object = None) -> EvaluationSummary:
        metrics = pq.read_table(run_root / "tables" / "clip_metrics.parquet").to_pydict()
        raw_count = int(sum(metrics["raw_detection_count"]))
        cleaned_count = int(sum(metrics["selected_detection_count"]))
        rejected_count = int(sum(metrics["rejected_detection_count"]))
        summary = EvaluationSummary(
            raw_detection_count=raw_count,
            cleaned_detection_count=cleaned_count,
            rejected_detection_count=rejected_count,
            interpolated_detection_count=0,
            false_positive_delta=max(raw_count - cleaned_count, 0),
        )
        output = run_root / "evaluation.json"
        output.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        return summary
