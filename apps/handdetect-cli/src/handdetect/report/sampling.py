from __future__ import annotations

import json
from pathlib import Path


class SampleManifestBuilder:
    def build(self, run_root: Path) -> Path:
        output = run_root / "report" / "sample-manifest.json"
        samples: list[dict[str, object]] = []
        for cleaned_path in sorted((run_root / "cleaned").glob("*.json")):
            payload = json.loads(cleaned_path.read_text(encoding="utf-8"))
            selected = [item for item in payload["detections"] if item["selected"]]
            if not selected:
                continue
            first = selected[0]
            samples.append(
                {
                    "clip_id": payload["clip_id"],
                    "frame": first["frame"],
                    "track_id": first["track_id"],
                    "detection_id": first["detection_id"],
                    "image_name": f"{payload['clip_id']}_frame_{int(first['frame']):06d}.png",
                }
            )
        output.write_text(
            json.dumps({"samples": samples, "policy": "one selected frame per clip"}, indent=2),
            encoding="utf-8",
        )
        return output
