from __future__ import annotations

from pathlib import Path

from dq_contracts.ids import ClipId, ExperimentId, RunId, RunSuiteId
from pydantic import BaseModel, ConfigDict


class SeedManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_root: Path
    dataset_file_count: int
    clip_count: int
    smoke_clip_ids: tuple[ClipId, ...]


class RunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: RunId
    run_suite_id: RunSuiteId
    experiment_id: ExperimentId
    data_root: Path
    output_root: Path
    config_path: Path
    clip_ids: tuple[ClipId, ...]
    config_sha256: str
    code_version: str
    label_set_id: str
    baseline_run: str | None = None


class RunIndexRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: RunId
    run_suite_id: RunSuiteId
    experiment_id: ExperimentId
    code_version: str
    config_sha256: str
    clip_count: int


class ClipRunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    clip_id: str
    interpolated_detection_count: int
    max_detections_per_frame: int
    selected_detection_count: int
    raw_detection_count: int
    rejected_detection_count: int
