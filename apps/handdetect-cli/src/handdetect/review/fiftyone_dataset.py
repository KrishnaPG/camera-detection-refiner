from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import pyarrow.parquet as pq
from dq_contracts.ids import RunId, RunSuiteId

_SESSIONS: dict[str, Any] = {}


class FiftyOneDatasetPublisher:
    def publish(
        self, suite_id: RunSuiteId, run_id: RunId, run_root: Path
    ) -> tuple[str, str | None]:
        manifest = json.loads(
            (run_root / "review" / "fiftyone-dataset.json").read_text(encoding="utf-8")
        )
        dataset_name = manifest["dataset_name"]
        try:
            import fiftyone as fo
        except Exception:
            return dataset_name, None
        try:
            self._reset_dataset(fo, dataset_name)
            dataset = fo.Dataset(dataset_name)
            dataset.persistent = True
            for sample in manifest["samples"]:
                dataset.add_sample(self._build_sample(fo, run_root, sample))
            dataset.save()
            session = fo.launch_app(dataset, address="0.0.0.0", port=5151, remote=True, auto=False)
        except Exception:
            return dataset_name, None
        _SESSIONS[dataset_name] = session
        return dataset_name, f"http://localhost:{session.server_port}"

    def _reset_dataset(self, fo: Any, dataset_name: str) -> None:
        if fo.dataset_exists(dataset_name):
            fo.delete_dataset(dataset_name)

    def _build_sample(self, fo: Any, run_root: Path, sample: dict[str, Any]) -> Any:
        image_path = run_root / "report" / "samples" / str(sample["image_name"])
        height, width = self._image_size(image_path)
        clip_id = str(sample["clip_id"])
        frame_index = int(sample["frame"])
        detections = self._load_detections(run_root, clip_id, frame_index)
        decisions = self._load_decisions(run_root, clip_id, frame_index)
        decision_by_id = {item["detection_id"]: item for item in decisions}
        result = fo.Sample(filepath=str(image_path))
        result["clip_id"] = clip_id
        result["frame_index"] = frame_index
        result["track_id"] = sample.get("track_id")
        result["raw"] = fo.Detections(
            detections=[self._to_label(fo, row, width, height) for row in detections]
        )
        result["cleaned"] = fo.Detections(
            detections=[
                self._to_label(fo, row, width, height)
                for row in detections
                if decision_by_id.get(row["detection_id"], {}).get("decision") == "kept"
            ],
        )
        result["rejected"] = fo.Detections(
            detections=[
                self._to_label(fo, row, width, height)
                for row in detections
                if decision_by_id.get(row["detection_id"], {}).get("decision")
                in {"rejected", "merged"}
            ],
        )
        result["stage_reasons"] = [
            self._stage_reason(decision)
            for decision in decisions
            if self._stage_reason(decision) is not None
        ]
        result["hard_case_tags"] = sorted(
            {
                reason
                for reason in result["stage_reasons"]
                if "duplicate" in reason or "shape" in reason or "temporal" in reason
            },
        )
        return result

    def _image_size(self, image_path: Path) -> tuple[int, int]:
        frame = cv2.imread(str(image_path))
        if frame is None:
            return 1, 1
        return int(frame.shape[0]), int(frame.shape[1])

    def _load_detections(
        self,
        run_root: Path,
        clip_id: str,
        frame_index: int,
    ) -> list[dict[str, Any]]:
        table = pq.read_table(run_root / "tables" / f"detections_{clip_id}.parquet")
        rows = table.to_pylist()
        return [row for row in rows if int(row["frame_index"]) == frame_index]

    def _load_decisions(
        self,
        run_root: Path,
        clip_id: str,
        frame_index: int,
    ) -> list[dict[str, Any]]:
        table = pq.read_table(run_root / "tables" / f"decisions_{clip_id}.parquet")
        rows = table.to_pylist()
        return [
            row for row in rows if row["clip_id"] == clip_id and int(row["frame"]) == frame_index
        ]

    def _to_label(self, fo: Any, row: dict[str, Any], width: int, height: int) -> Any:
        x1 = float(row["x1"])
        y1 = float(row["y1"])
        x2 = float(row["x2"])
        y2 = float(row["y2"])
        bbox = [x1 / width, y1 / height, max((x2 - x1) / width, 0.0), max((y2 - y1) / height, 0.0)]
        return fo.Detection(
            label="hand",
            bounding_box=bbox,
            confidence=float(row["confidence"]),
            detection_id=row["detection_id"],
            selected=bool(row["selected"]),
        )

    def _stage_reason(self, decision: dict[str, Any]) -> str | None:
        stage = str(decision.get("stage") or "").strip()
        reason = str(decision.get("reason") or "").strip()
        if not stage and not reason:
            return None
        if not reason:
            return stage
        return f"{stage}:{reason}"
