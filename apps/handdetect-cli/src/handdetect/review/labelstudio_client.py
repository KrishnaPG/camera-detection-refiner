from __future__ import annotations

import json
from pathlib import Path

from label_studio_sdk import Client


class LabelStudioPublisher:
    def publish(
        self,
        run_root: Path,
        url: str,
        token: str,
    ) -> tuple[int, int]:
        tasks_path = run_root / "review" / "labelstudio-tasks.json"
        tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
        client = Client(url=url, api_key=token)
        title = f"handdetect-{run_root.parent.name}-{run_root.name}"
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
        output = run_root / "review" / "labelstudio-import.json"
        output.write_text(
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
