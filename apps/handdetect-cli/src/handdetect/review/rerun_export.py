from __future__ import annotations

import json
from pathlib import Path
from typing import cast
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict

JsonMap = dict[str, object]
JsonRows = list[JsonMap]

RERUN_COLOR_BY_DECISION = {
    "kept": [48, 209, 88, 255],
    "merged": [255, 214, 10, 255],
    "rejected": [255, 69, 58, 255],
}


class RerunExportConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    public_url: str = ""
    workbench_public_url: str = ""


class RerunExportResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    path: Path
    url: str | None
    message: str
    recording_url: str | None = None


class RerunRecordingExporter:
    def export(self, run_root: Path, config: RerunExportConfig) -> RerunExportResult:
        review_root = run_root / "review"
        output = review_root / "rerun-handoff.json"
        recording_path = review_root / "rerun" / "handdetect-review.rrd"
        recording_url = self._recording_url(run_root, config)
        viewer_url = self._viewer_url(recording_url, config)

        try:
            self._write_recording(run_root, recording_path, config)
        except Exception as exc:
            message = f"Rerun recording fallback: {exc}"
            self._write_handoff(
                output,
                run_root,
                "handoff_file",
                message,
                recording_path if recording_path.exists() else None,
                recording_url,
                viewer_url,
            )
            return RerunExportResult(
                status="handoff_file",
                path=output,
                url=viewer_url,
                message=message,
                recording_url=recording_url,
            )

        message = "Rerun temporal MOT recording created"
        self._write_handoff(
            output,
            run_root,
            "ready",
            message,
            recording_path,
            recording_url,
            viewer_url,
        )
        return RerunExportResult(
            status="ready",
            path=recording_path,
            url=viewer_url,
            message=message,
            recording_url=recording_url,
        )

    def _write_recording(
        self,
        run_root: Path,
        recording_path: Path,
        config: RerunExportConfig,
    ) -> None:
        import rerun as rr  # type: ignore[import-untyped]

        story = _read_json(run_root / "review" / "story.json")
        recording_path.parent.mkdir(parents=True, exist_ok=True)
        recording = rr.RecordingStream(
            f"handdetect-{_string_value(story.get('run_suite_id'))}-{_string_value(story.get('run_id'))}"
        )
        recording.save(recording_path)
        recording.log(
            "legend",
            rr.AnnotationContext(
                [
                    rr.ClassDescription(
                        info=rr.AnnotationInfo(
                            id=1,
                            label="approved hand track",
                            color=RERUN_COLOR_BY_DECISION["kept"],
                        )
                    ),
                    rr.ClassDescription(
                        info=rr.AnnotationInfo(
                            id=2,
                            label="rejected detection",
                            color=RERUN_COLOR_BY_DECISION["rejected"],
                        )
                    ),
                    rr.ClassDescription(
                        info=rr.AnnotationInfo(
                            id=3,
                            label="duplicate detection",
                            color=RERUN_COLOR_BY_DECISION["merged"],
                        )
                    ),
                ]
            ),
            static=True,
        )
        clips = story.get("clips")
        if not isinstance(clips, list):
            return
        for clip in clips:
            clip_row = _mapping_value(clip)
            self._log_clip(recording, rr, run_root, clip_row, config)

    def _log_clip(
        self,
        recording: object,
        rr_module: object,
        run_root: Path,
        clip: JsonMap,
        config: RerunExportConfig,
    ) -> None:
        rr = rr_module
        clip_id = _string_value(clip.get("clip_id"))
        fps = max(_float_value(clip.get("fps")), 1.0)
        video_path = run_root / _string_value(clip.get("compare_overlay_url"))
        video_entity = f"{clip_id}/compare_video"
        if video_path.exists() and video_path.is_file():
            recording.log(  # type: ignore[attr-defined]
                video_entity,
                rr.AssetVideo(contents=video_path.read_bytes(), media_type="video/mp4"),
                static=True,
            )
        boxes_payload = _read_json(run_root / _string_value(clip.get("boxes_path")))
        frames = boxes_payload.get("frames")
        if not isinstance(frames, list):
            return
        for frame_row in frames:
            frame = _mapping_value(frame_row)
            frame_index = _int_value(frame.get("frame"))
            recording.set_time("frame", sequence=frame_index)  # type: ignore[attr-defined]
            recording.set_time("time", duration=frame_index / fps)  # type: ignore[attr-defined]
            recording.log(  # type: ignore[attr-defined]
                video_entity,
                rr.VideoFrameReference(
                    seconds=frame_index / fps,
                    video_reference=video_entity,
                ),
            )
            boxes = _list_value(frame.get("boxes"))
            self._log_box_group(
                recording, rr, f"{clip_id}/raw_detector", boxes, {"kept", "rejected", "merged"}
            )
            self._log_box_group(recording, rr, f"{clip_id}/adapter_approved", boxes, {"kept"})
            self._log_box_group(
                recording, rr, f"{clip_id}/adapter_rejected", boxes, {"rejected", "merged"}
            )

    def _log_box_group(
        self,
        recording: object,
        rr: object,
        entity_path: str,
        boxes: JsonRows,
        decisions: set[str],
    ) -> None:
        selected = [box for box in boxes if _string_value(box.get("decision")) in decisions]
        if not selected:
            return
        mins = [[_float_value(box.get("x1")), _float_value(box.get("y1"))] for box in selected]
        sizes = [
            [
                max(_float_value(box.get("x2")) - _float_value(box.get("x1")), 0.0),
                max(_float_value(box.get("y2")) - _float_value(box.get("y1")), 0.0),
            ]
            for box in selected
        ]
        recording.log(  # type: ignore[attr-defined]
            entity_path,
            rr.Boxes2D(
                mins=mins,
                sizes=sizes,
                labels=[_box_label(box) for box in selected],
                colors=[
                    RERUN_COLOR_BY_DECISION.get(
                        _string_value(box.get("decision")),
                        RERUN_COLOR_BY_DECISION["rejected"],
                    )
                    for box in selected
                ],
                show_labels=True,
            ),
        )

    def _recording_url(self, run_root: Path, config: RerunExportConfig) -> str | None:
        if not config.workbench_public_url:
            return None
        return (
            f"{config.workbench_public_url.rstrip('/')}/artifacts/"
            f"{run_root.parent.name}/{run_root.name}/review/rerun/handdetect-review.rrd"
        )

    def _viewer_url(self, recording_url: str | None, config: RerunExportConfig) -> str | None:
        if not config.public_url:
            return recording_url
        if not recording_url:
            return config.public_url.rstrip("/")
        return f"{config.public_url.rstrip('/')}/?url={quote(recording_url, safe='')}"

    def _write_handoff(
        self,
        output: Path,
        run_root: Path,
        status: str,
        message: str,
        recording_path: Path | None,
        recording_url: str | None,
        viewer_url: str | None,
    ) -> None:
        payload = {
            "tool": "rerun",
            "handoff_type": "temporal_mot_playback",
            "status": status,
            "message": message,
            "run_suite_id": run_root.parent.name,
            "run_id": run_root.name,
            "source": "review/story.json",
            "recording_path": str(recording_path.relative_to(run_root)) if recording_path else None,
            "recording_url": recording_url,
            "viewer_url": viewer_url,
            "tracks": "review/clips/*/tracks.json",
            "boxes": "review/clips/*/boxes.json",
            "videos": "review/clips/*/compare_raw_adapter.mp4",
        }
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _box_label(box: JsonMap) -> str:
    decision = _string_value(box.get("decision"))
    reason = _string_value(box.get("reason"))
    stage = _string_value(box.get("stage"))
    track_id = box.get("track_id")
    prefix = reason or stage or decision
    suffix = f"track {track_id}" if track_id is not None else "no track"
    return f"{prefix} | {suffix}"


def _read_json(path: Path) -> JsonMap:
    return cast(JsonMap, json.loads(path.read_text(encoding="utf-8")))


def _mapping_value(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _list_value(value: object) -> JsonRows:
    if not isinstance(value, list):
        return []
    return [_mapping_value(row) for row in value]


def _string_value(value: object) -> str:
    return str(value) if value is not None else ""


def _int_value(value: object) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _float_value(value: object) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
