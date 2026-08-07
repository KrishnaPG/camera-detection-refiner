from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class PlatformStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    path: str
    error: str | None = None
    run_id: str | None = None
    url: str | None = None


class TrackingExportStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    mlflow: PlatformStatus
    dvc: PlatformStatus
    evidently: PlatformStatus


class TrackingExportStatusWriter:
    def write(self, status: TrackingExportStatus, run_root: Path) -> Path:
        output = run_root / "tracking_export_status.json"
        output.write_text(json.dumps(status.model_dump(mode="json"), indent=2), encoding="utf-8")
        return output
