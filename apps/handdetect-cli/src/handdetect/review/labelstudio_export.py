from __future__ import annotations

import json
import os
from pathlib import Path

import cv2
import pyarrow.parquet as pq


class LabelStudioExporter:
    def export_tasks(self, run_root: Path, base_url: str | None = None) -> Path:
        resolved_base_url = base_url or os.environ.get(
            "HANDDETECT_WORKBENCH_PUBLIC_URL", "http://127.0.0.1:8000"
        )
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
                            f"{resolved_base_url.rstrip('/')}/artifacts/"
                            f"{run_manifest['run_suite_id']}/{run_manifest['run_id']}"
                            f"/report/samples/{sample['image_name']}"
                        ),
                        "clip_id": sample["clip_id"],
                        "frame": sample["frame"],
                    },
                    "predictions": [self._prediction_for_sample(run_root, sample)],
                }
            )
        output = run_root / "review" / "labelstudio-tasks.json"
        output.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        return output

    def _prediction_for_sample(
        self, run_root: Path, sample: dict[str, object]
    ) -> dict[str, object]:
        image_path = run_root / "report" / "samples" / str(sample["image_name"])
        width, height = self._image_size(image_path)
        rows = self._selected_rows(
            run_root,
            str(sample["clip_id"]),
            int(sample["frame"]),
        )
        return {
            "model_version": "handdetect-cleaned",
            "score": self._mean_confidence(rows),
            "result": [self._rectangle_result(row, width, height) for row in rows],
        }

    def _selected_rows(
        self,
        run_root: Path,
        clip_id: str,
        frame_index: int,
    ) -> list[dict[str, object]]:
        table = pq.read_table(run_root / "tables" / f"detections_{clip_id}.parquet")
        return [
            row
            for row in table.to_pylist()
            if int(row["frame_index"]) == frame_index and bool(row["selected"])
        ]

    def _image_size(self, image_path: Path) -> tuple[int, int]:
        frame = cv2.imread(str(image_path))
        if frame is None:
            return 1, 1
        return int(frame.shape[1]), int(frame.shape[0])

    def _rectangle_result(
        self,
        row: dict[str, object],
        width: int,
        height: int,
    ) -> dict[str, object]:
        x1 = float(row["x1"])
        y1 = float(row["y1"])
        x2 = float(row["x2"])
        y2 = float(row["y2"])
        return {
            "id": str(row["detection_id"]),
            "from_name": "label",
            "to_name": "image",
            "type": "rectanglelabels",
            "origin": "prediction",
            "score": float(row["confidence"]),
            "original_width": width,
            "original_height": height,
            "image_rotation": 0,
            "value": {
                "x": x1 * 100.0 / width,
                "y": y1 * 100.0 / height,
                "width": max((x2 - x1) * 100.0 / width, 0.0),
                "height": max((y2 - y1) * 100.0 / height, 0.0),
                "rotation": 0,
                "rectanglelabels": ["hand"],
            },
        }

    def _mean_confidence(self, rows: list[dict[str, object]]) -> float:
        if not rows:
            return 0.0
        return sum(float(row["confidence"]) for row in rows) / len(rows)
