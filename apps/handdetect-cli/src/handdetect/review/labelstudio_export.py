from __future__ import annotations

import json
from pathlib import Path


class LabelStudioExporter:
    def export_tasks(self, run_root: Path, base_url: str = "http://localhost:8000") -> Path:
        manifest = json.loads(
            (run_root / "report" / "sample-manifest.json").read_text(encoding="utf-8")
        )
        run_manifest = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
        tasks = []
        for index, sample in enumerate(manifest["samples"], start=1):
            tasks.append(
                {
                    "id": index,
                    "data": {
                        "image": (
                            f"{base_url}/artifacts/{run_manifest['run_suite_id']}/{run_manifest['run_id']}"
                            f"/report/samples/{sample['image_name']}"
                        ),
                        "clip_id": sample["clip_id"],
                        "frame": sample["frame"],
                    },
                    "predictions": [
                        {
                            "model_version": "handdetect-cleaned",
                            "result": [],
                        }
                    ],
                }
            )
        output = run_root / "review" / "labelstudio-tasks.json"
        output.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        return output
