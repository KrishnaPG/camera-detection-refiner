from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import datumaro as dm

HOST = os.environ.get("HANDDETECT_DATUMARO_BIND_HOST", "0.0.0.0")
PORT = int(os.environ.get("HANDDETECT_DATUMARO_CONTAINER_PORT", "8000"))
RUNS_ROOT = Path(os.environ.get("HANDDETECT_RUNS_ROOT", "/tmp/handdetect/runs")).resolve()
LABEL_NAMES = (
    "adapter_approved",
    "adapter_rejected",
    "duplicate_detections",
    "implausible_detection",
    "unsupported_detection",
)


class ExporterHandler(BaseHTTPRequestHandler):
    server_version = "handdetect-datumaro-exporter/1.0"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._write_json(200, {"status": "ok", "datumaro_version": dm.__version__})
            return
        self._write_json(404, {"status": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/export":
            self._write_json(404, {"status": "not_found"})
            return
        try:
            content_length = int(self.headers.get("Content-Length") or "0")
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            response = export_datumaro(payload)
            self._write_json(200, response)
        except Exception as exc:
            self._write_json(500, {"status": "error", "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(
            json.dumps(
                {
                    "event": "http_request",
                    "client": self.address_string(),
                    "message": format % args,
                }
            )
        )

    def _write_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def export_datumaro(payload: dict[str, object]) -> dict[str, object]:
    run_root = _validated_run_root(str(payload["run_root"]))
    frames = _frame_rows(payload.get("frames"))
    export_root = run_root / "review" / "datumaro"
    adapter_root = export_root / "adapter-output"
    frozen_root = export_root / "frozen-labels"
    diff_path = export_root / "diff-manifest.json"
    export_root.mkdir(parents=True, exist_ok=True)
    label_ids = {label: index for index, label in enumerate(_label_names(frames))}
    adapter_summary = _export_dataset(adapter_root, frames, label_ids, include_boxes=True)
    frozen_summary = _export_dataset(frozen_root, frames, label_ids, include_boxes=False)
    source_manifests = _dict_value(payload.get("source_manifests"))
    diff_payload = _diff_payload(run_root, adapter_summary, frozen_summary, source_manifests)
    _write_json(diff_path, diff_payload)
    return {
        "status": "ready",
        "message": "Datumaro isolated tool container exported projects and diff manifest",
        "datumaro_version": dm.__version__,
        "export_root": str(export_root),
        "diff_path": str(diff_path),
        "adapter_output": adapter_summary,
        "frozen_labels": frozen_summary,
    }


def _export_dataset(
    output_dir: Path,
    frames: list[dict[str, object]],
    label_ids: dict[str, int],
    *,
    include_boxes: bool,
) -> dict[str, object]:
    label_counts: Counter[str] = Counter()
    items = []
    for frame in frames:
        annotations = []
        if include_boxes:
            for box_index, box in enumerate(_box_rows(frame.get("boxes"))):
                label = str(box["label"])
                label_counts[label] += 1
                annotations.append(
                    dm.Bbox(
                        float(box["x1"]),
                        float(box["y1"]),
                        max(float(box["x2"]) - float(box["x1"]), 0.0),
                        max(float(box["y2"]) - float(box["y1"]), 0.0),
                        id=box_index,
                        label=label_ids[label],
                        attributes={
                            "clip_id": str(frame["clip_id"]),
                            "frame": int(frame["frame"]),
                            "adapter_label": label,
                        },
                    )
                )
        items.append(
            dm.DatasetItem(
                id=f"{frame['clip_id']}_{int(frame['frame']):06d}",
                subset="review",
                media=dm.Image.from_file(path=str(frame["image_path"])),
                annotations=annotations,
                attributes={"clip_id": str(frame["clip_id"]), "frame": int(frame["frame"])},
            )
        )
    dataset = dm.Dataset.from_iterable(
        items,
        categories={dm.AnnotationType.label: _label_categories(label_ids)},
    )
    dataset.export(str(output_dir), format="datumaro", save_media=False)
    return {
        "item_count": len(items),
        "annotation_count": int(sum(label_counts.values())),
        "label_counts": dict(sorted(label_counts.items())),
        "project_path": str(output_dir),
        "project_sha256": _tree_hash(output_dir),
        "media_copy_mode": "zero_copy_absolute_media_references",
    }


def _diff_payload(
    run_root: Path,
    adapter_summary: dict[str, object],
    frozen_summary: dict[str, object],
    source_manifests: dict[str, object],
) -> dict[str, object]:
    manifest = _read_json(run_root / "run-manifest.json")
    replay_lock_path = run_root / "lineage" / "replay.lock.json"
    replay_lock = _read_json(replay_lock_path) if replay_lock_path.exists() else {}
    label_ref = replay_lock.get("labels") if isinstance(replay_lock.get("labels"), dict) else {}
    adapter_counts = _counts(adapter_summary.get("label_counts"))
    frozen_counts = _counts(frozen_summary.get("label_counts"))
    labels = sorted(set(adapter_counts) | set(frozen_counts))
    return {
        "tool": "datumaro",
        "datumaro_version": dm.__version__,
        "handoff_type": "dataset_export_and_diff",
        "run_suite_id": run_root.parent.name,
        "run_id": run_root.name,
        "experiment_id": str(manifest.get("experiment_id") or ""),
        "label_set_id": str(manifest.get("label_set_id") or ""),
        "label_set_ref": label_ref,
        "source_manifests": source_manifests
        or {
            "story": "review/story.json",
            "platforms": "review/platforms.json",
            "labelstudio_tasks": "review/labelstudio-tasks.json",
            "replay_lock": "lineage/replay.lock.json",
        },
        "exports": {
            "adapter_output": adapter_summary,
            "frozen_labels": frozen_summary,
        },
        "label_deltas": [
            {
                "label": label,
                "adapter_output_count": adapter_counts.get(label, 0),
                "frozen_label_count": frozen_counts.get(label, 0),
                "delta": adapter_counts.get(label, 0) - frozen_counts.get(label, 0),
            }
            for label in labels
        ],
        "regression_keys": {
            "adapter_annotation_count": int(adapter_summary["annotation_count"]),
            "frozen_annotation_count": int(frozen_summary["annotation_count"]),
            "delta_annotation_count": int(adapter_summary["annotation_count"])
            - int(frozen_summary["annotation_count"]),
        },
        "media_policy": {
            "copy_state": "not_copied",
            "mode": "zero_copy_absolute_media_references",
            "reason": "Datumaro annotations reference existing immutable run sample images.",
        },
    }


def _label_categories(label_ids: dict[str, int]) -> dm.LabelCategories:
    categories = dm.LabelCategories()
    for label in sorted(label_ids, key=label_ids.__getitem__):
        categories.add(label)
    return categories


def _label_names(frames: list[dict[str, object]]) -> tuple[str, ...]:
    labels = set(LABEL_NAMES)
    for frame in frames:
        labels.update(str(box["label"]) for box in _box_rows(frame.get("boxes")))
    return tuple(sorted(labels))


def _validated_run_root(value: str) -> Path:
    run_root = Path(value).resolve()
    if RUNS_ROOT not in run_root.parents:
        raise ValueError(f"run_root must be under {RUNS_ROOT}: {run_root}")
    return run_root


def _frame_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ValueError("frames must be a list")
    return [frame for frame in value if isinstance(frame, dict)]


def _box_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [box for box in value if isinstance(box, dict)]


def _counts(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {str(key): int(count) for key, count in value.items()}


def _dict_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return parsed


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), ExporterHandler)
    print(json.dumps({"event": "datumaro_exporter_started", "host": HOST, "port": PORT}))
    server.serve_forever()


if __name__ == "__main__":
    main()
