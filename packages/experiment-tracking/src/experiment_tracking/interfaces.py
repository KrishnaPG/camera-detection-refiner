from __future__ import annotations

from pathlib import Path

from dq_contracts.ids import ExperimentId, RunId, RunSuiteId
from pydantic import BaseModel, ConfigDict


class TrackingMetric(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: float


class TrackingRunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_suite_id: RunSuiteId
    run_id: RunId
    experiment_id: ExperimentId
    config_sha256: str
    dataset_file_count: int
    clip_count: int
    metrics: tuple[TrackingMetric, ...]
    artifact_paths: tuple[Path, ...]
    run_root: Path
