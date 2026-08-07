from __future__ import annotations

import hashlib
import json
from pathlib import Path

from label_studio_sdk import Client

LABEL_STUDIO_PROJECT_TITLE_MAX_LENGTH = 50


class LabelStudioPublisher:
    def publish(
        self,
        run_root: Path,
        url: str,
        token: str,
    ) -> tuple[int, int]:
        existing = run_root / "review" / "labelstudio-import.json"
        if existing.exists():
            payload = json.loads(existing.read_text(encoding="utf-8"))
            return int(payload["project_id"]), int(payload.get("imported_task_count", 0))
        tasks_path = run_root / "review" / "labelstudio-tasks.json"
        tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
        client = Client(url=url, api_key=token)
        title = label_studio_project_title(run_root)
        project = client.start_project(
            title=title,
            label_config=(
                '<View><Image name="image" value="$image"/>'
                '<RectangleLabels name="label" toName="image">'
                '<Label value="hand"/></RectangleLabels></View>'
            ),
        )
        imported = project.import_tasks(tasks)
        import_count = len(imported) if isinstance(imported, list) else len(tasks)
        existing.write_text(
            json.dumps(
                {
                    "project_id": project.id,
                    "url": f"{url.rstrip('/')}/projects/{project.id}",
                    "imported_task_count": import_count,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return int(project.id), int(import_count)


def label_studio_project_title(run_root: Path) -> str:
    run_ref = f"{run_root.parent.name}-{run_root.name}"
    digest = hashlib.sha256(run_ref.encode("utf-8")).hexdigest()[:10]
    prefix = f"handdetect-{digest}-"
    suffix_budget = LABEL_STUDIO_PROJECT_TITLE_MAX_LENGTH - len(prefix)
    suffix = run_ref[-suffix_budget:]
    title = f"{prefix}{suffix}"
    if len(title) > LABEL_STUDIO_PROJECT_TITLE_MAX_LENGTH:
        raise ValueError(f"Label Studio project title exceeds limit: {title}")
    return title
