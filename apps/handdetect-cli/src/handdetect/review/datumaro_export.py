from __future__ import annotations

import json
import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class DatumaroHandoffResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    path: Path
    url: str | None
    message: str


class DatumaroHandoffExporter:
    def export(self, run_root: Path, public_url: str) -> DatumaroHandoffResult:
        output = run_root / "review" / "datumaro-handoff.json"
        datumaro_cli = shutil.which("datumaro")
        status = "cli_ready" if datumaro_cli else "handoff_file"
        message = (
            "Datumaro CLI available for conversion/diff"
            if datumaro_cli
            else "Datumaro handoff manifest written; run Datumaro in an isolated tool image"
        )
        payload = {
            "tool": "datumaro",
            "handoff_type": "dataset_diff",
            "status": status,
            "message": message,
            "run_suite_id": run_root.parent.name,
            "run_id": run_root.name,
            "input_manifests": {
                "story": "review/story.json",
                "boxes": "review/clips/*/boxes.json",
                "frozen_labels": "labels/versions/<label_set_id>/",
            },
            "supported_operations": [
                "convert predictions to Datumaro project in an isolated tool container",
                "diff baseline labels against this run's adapter output",
                "write diff manifest back to review/platforms.json",
            ],
            "local_cli_available": datumaro_cli is not None,
            "local_cli_path": datumaro_cli,
        }
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        url = public_url.rstrip("/") if public_url else None
        return DatumaroHandoffResult(
            status=status,
            path=output,
            url=url,
            message=message,
        )


class RerunHandoffExporter:
    def export(self, run_root: Path) -> DatumaroHandoffResult:
        output = run_root / "review" / "rerun-handoff.json"
        status = "handoff_file"
        message = "Rerun temporal playback handoff manifest written"
        payload = {
            "tool": "rerun",
            "handoff_type": "temporal_mot_playback",
            "status": status,
            "message": message,
            "run_suite_id": run_root.parent.name,
            "run_id": run_root.name,
            "source": "review/story.json",
            "tracks": "review/clips/*/tracks.json",
            "boxes": "review/clips/*/boxes.json",
            "videos": "review/clips/*/compare_raw_adapter.mp4",
        }
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return DatumaroHandoffResult(
            status=status,
            path=output,
            url=None,
            message=message,
        )
