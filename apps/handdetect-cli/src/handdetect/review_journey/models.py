from __future__ import annotations

from pathlib import Path

from dq_contracts.ids import RunId, RunSuiteId
from pydantic import BaseModel, ConfigDict


class ReviewPlatformStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    url: str | None
    path: Path | None
    message: str
    project_id: int | None = None
    imported_task_count: int | None = None
    task_id: int | None = None
    job_ids: tuple[int, ...] = ()
    job_urls: tuple[str, ...] = ()
    recording_url: str | None = None
    correction_path: Path | None = None
    label_set_id: str | None = None
    annotation_sha256: str | None = None
    shape_count: int | None = None


class ReviewPlatformManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_suite_id: RunSuiteId
    run_id: RunId
    report: ReviewPlatformStatus
    biodock: ReviewPlatformStatus
    mlflow: ReviewPlatformStatus
    dvc: ReviewPlatformStatus
    evidently: ReviewPlatformStatus
    fiftyone: ReviewPlatformStatus
    label_studio: ReviewPlatformStatus
    cvat: ReviewPlatformStatus
    datumaro: ReviewPlatformStatus
    rerun: ReviewPlatformStatus
    fiftyone_dataset: str
