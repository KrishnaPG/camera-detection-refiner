from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class CvatHandoffResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    path: Path
    url: str | None
    message: str
    imported_task_count: int


class CvatHandoffExporter:
    def export(self, run_root: Path, public_url: str) -> CvatHandoffResult:
        review_root = run_root / "review"
        tasks_path = review_root / "labelstudio-tasks.json"
        output = review_root / "cvat-handoff.json"
        imported_count = self._task_count(tasks_path)
        url = public_url.rstrip("/") if public_url else None
        status = "handoff_ready" if url else "handoff_file"
        message = (
            "CVAT service available; create review tasks from handoff manifest"
            if url
            else (
                "CVAT handoff manifest written; configure HANDDETECT_CVAT_PUBLIC_URL "
                "to link service"
            )
        )
        payload = {
            "tool": "cvat",
            "handoff_type": "annotation_review",
            "status": status,
            "message": message,
            "source_tasks_path": str(tasks_path.relative_to(run_root)),
            "run_suite_id": run_root.parent.name,
            "run_id": run_root.name,
            "label_schema": {"labels": [{"name": "hand", "type": "rectangle"}]},
            "task_count": imported_count,
            "review_artifacts": {
                "story": "review/story.json",
                "platforms": "review/platforms.json",
                "clips": "review/clips/*",
            },
        }
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return CvatHandoffResult(
            status=status,
            path=output,
            url=url,
            message=message,
            imported_task_count=imported_count,
        )

    def _task_count(self, tasks_path: Path) -> int:
        if not tasks_path.exists():
            return 0
        parsed = json.loads(tasks_path.read_text(encoding="utf-8"))
        if isinstance(parsed, list):
            return len(parsed)
        return 0
