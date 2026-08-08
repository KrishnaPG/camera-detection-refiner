from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from handdetect.review.cvat_export import build_review_frame_tasks
from pydantic import BaseModel, ConfigDict

DATUMARO_EXPORT_TIMEOUT_SECONDS = 180


class DatumaroHandoffResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    path: Path
    url: str | None
    message: str
    export_root: Path | None = None
    diff_path: Path | None = None


class DatumaroHandoffExporter:
    def export(
        self,
        run_root: Path,
        public_url: str,
        internal_url: str = "",
    ) -> DatumaroHandoffResult:
        output = run_root / "review" / "datumaro-handoff.json"
        diff_path = run_root / "review" / "datumaro" / "diff-manifest.json"
        export_root = run_root / "review" / "datumaro"
        if not internal_url.strip():
            message = "Datumaro exporter service is not configured"
            self._write_handoff(
                output=output,
                run_root=run_root,
                status="not_configured",
                message=message,
                diff_path=None,
                export_root=export_root,
                diff_url=None,
                tool_response={},
            )
            return DatumaroHandoffResult(
                status="not_configured",
                path=output,
                url=None,
                message=message,
            )

        payload = _export_request(run_root, public_url)
        try:
            response = _post_json(
                f"{internal_url.rstrip('/')}/export",
                payload,
                DATUMARO_EXPORT_TIMEOUT_SECONDS,
            )
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            message = f"Datumaro exporter service fallback: {exc}"
            self._write_handoff(
                output=output,
                run_root=run_root,
                status="handoff_ready",
                message=message,
                diff_path=None,
                export_root=export_root,
                diff_url=None,
                tool_response={},
            )
            return DatumaroHandoffResult(
                status="handoff_ready",
                path=output,
                url=None,
                message=message,
            )

        status = str(response.get("status") or "unknown")
        message = str(response.get("message") or "Datumaro exporter returned no message")
        diff_url = public_url.rstrip("/") if public_url and status == "ready" else None
        self._write_handoff(
            output=output,
            run_root=run_root,
            status=status,
            message=message,
            diff_path=diff_path if status == "ready" else None,
            export_root=export_root,
            diff_url=diff_url,
            tool_response=response,
        )
        return DatumaroHandoffResult(
            status=status,
            path=output,
            url=diff_url,
            message=message,
            export_root=export_root if status == "ready" else None,
            diff_path=diff_path if status == "ready" else None,
        )

    def _write_handoff(
        self,
        *,
        output: Path,
        run_root: Path,
        status: str,
        message: str,
        diff_path: Path | None,
        export_root: Path,
        diff_url: str | None,
        tool_response: dict[str, object],
    ) -> None:
        payload = {
            "tool": "datumaro",
            "handoff_type": "dataset_export_and_diff",
            "status": status,
            "message": message,
            "run_suite_id": run_root.parent.name,
            "run_id": run_root.name,
            "input_manifests": {
                "story": "review/story.json",
                "boxes": "review/clips/*/boxes.json",
                "cvat_corrections": _run_relative(
                    run_root,
                    run_root / "review" / "cvat-corrections.json",
                ),
                "cvat_label_freeze": _run_relative(
                    run_root,
                    run_root / "review" / "cvat-label-freeze.json",
                ),
                "frozen_labels": _latest_frozen_label_manifest(run_root),
            },
            "outputs": {
                "export_root": _run_relative(run_root, export_root),
                "adapter_output_project": _run_relative(
                    run_root, export_root / "adapter-output"
                ),
                "frozen_labels_project": _run_relative(
                    run_root, export_root / "frozen-labels"
                ),
                "diff_manifest": _run_relative(run_root, diff_path) if diff_path else None,
                "diff_url": diff_url,
            },
            "tool_response": tool_response,
            "media_policy": {
                "copy_state": "not_copied",
                "mode": "zero_copy_absolute_media_references",
            },
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _export_request(run_root: Path, public_url: str) -> dict[str, object]:
    frames = []
    for task in build_review_frame_tasks(run_root):
        frames.append(
            {
                "index": task.index,
                "clip_id": task.clip_id,
                "frame": task.frame,
                "image_path": str(task.image_path),
                "boxes": [
                    {
                        "label": box.label,
                        "x1": box.x1,
                        "y1": box.y1,
                        "x2": box.x2,
                        "y2": box.y2,
                    }
                    for box in task.boxes
                ],
            }
        )
    return {
        "run_root": str(run_root),
        "public_url": public_url,
        "frames": frames,
        "source_manifests": _source_manifests(run_root),
    }


def _post_json(url: str, payload: dict[str, object], timeout_seconds: int) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Unexpected Datumaro exporter response from {url}")
    return parsed


def _run_relative(run_root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path.relative_to(run_root))


def _source_manifests(run_root: Path) -> dict[str, object]:
    sources: dict[str, object] = {
        "story": "review/story.json",
        "labelstudio_tasks": "review/labelstudio-tasks.json",
    }
    cvat_corrections = run_root / "review" / "cvat-corrections.json"
    if cvat_corrections.exists():
        sources["cvat_corrections"] = _read_json(cvat_corrections)
    cvat_freeze = run_root / "review" / "cvat-label-freeze.json"
    if cvat_freeze.exists():
        sources["cvat_label_freeze"] = _read_json(cvat_freeze)
    frozen_manifest = _latest_frozen_label_manifest(run_root)
    if frozen_manifest:
        sources["frozen_labels"] = frozen_manifest
    return sources


def _latest_frozen_label_manifest(run_root: Path) -> str | None:
    label_root = run_root / "labels" / "versions"
    if not label_root.exists():
        return None
    manifests = sorted(label_root.glob("*/manifest.json"), key=lambda path: path.stat().st_mtime)
    return _run_relative(run_root, manifests[-1]) if manifests else None


def _read_json(path: Path) -> dict[str, object]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return parsed
