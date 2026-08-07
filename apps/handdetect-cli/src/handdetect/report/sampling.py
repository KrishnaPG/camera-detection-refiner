from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq


class SampleManifestBuilder:
    def build(self, run_root: Path) -> Path:
        output = run_root / "report" / "sample-manifest.json"
        samples: list[dict[str, object]] = []
        for cleaned_path in sorted((run_root / "cleaned").glob("*.json")):
            payload = json.loads(cleaned_path.read_text(encoding="utf-8"))
            frame = self._representative_frame(run_root, str(payload["clip_id"]))
            if frame is None:
                continue
            detection = self._first_frame_detection(payload["detections"], frame)
            track_id = detection.get("track_id") if detection is not None else None
            detection_id = detection.get("detection_id") if detection is not None else None
            samples.append(
                {
                    "clip_id": payload["clip_id"],
                    "frame": frame,
                    "track_id": track_id,
                    "detection_id": detection_id,
                    "image_name": f"{payload['clip_id']}_frame_{frame:06d}.png",
                }
            )
        output.write_text(
            json.dumps(
                {
                    "samples": samples,
                    "policy": "one visually interesting frame per clip",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return output

    def _representative_frame(self, run_root: Path, clip_id: str) -> int | None:
        detections_path = run_root / "tables" / f"detections_{clip_id}.parquet"
        decisions_path = run_root / "tables" / f"decisions_{clip_id}.parquet"
        if not detections_path.exists() or not decisions_path.exists():
            return None
        detections = pq.read_table(detections_path).to_pylist()
        decisions = {
            str(row["detection_id"]): str(row["decision"])
            for row in pq.read_table(decisions_path).to_pylist()
        }
        frame_scores: dict[int, dict[str, int]] = {}
        for row in detections:
            frame = int(row["frame_index"])
            score = frame_scores.setdefault(frame, {"raw": 0, "kept": 0, "rejected": 0})
            score["raw"] += 1
            if decisions.get(str(row["detection_id"])) == "kept":
                score["kept"] += 1
            else:
                score["rejected"] += 1
        if not frame_scores:
            return None
        return max(
            frame_scores,
            key=lambda frame: (
                frame_scores[frame]["rejected"],
                frame_scores[frame]["kept"],
                frame_scores[frame]["raw"],
                -frame,
            ),
        )

    def _first_frame_detection(
        self,
        detections: list[dict[str, object]],
        frame: int,
    ) -> dict[str, object] | None:
        for detection in detections:
            if int(detection["frame"]) == frame:
                return detection
        return None
