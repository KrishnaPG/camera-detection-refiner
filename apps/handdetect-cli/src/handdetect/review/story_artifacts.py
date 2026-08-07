from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import cast

import pyarrow.parquet as pq  # type: ignore[import-untyped]
from handdetect.review.story_constants import (
    ADAPTER_OVERLAY_FILE,
    BOX_INDEX_FILE,
    COMPARE_OVERLAY_FILE,
    DEFAULT_LAYOUT_ID,
    PACKAGE_ID,
    PLATFORM_LABELS,
    RAW_OVERLAY_FILE,
    REASON_LABELS,
    REJECTED_OVERLAY_FILE,
    SUPPORT_ROWS,
    THUMBNAIL_STRIP_FILE,
    WORKSPACE_ID,
)
from pydantic import BaseModel, ConfigDict, Field
from visual_reporting.review_media import (  # type: ignore[import-untyped]
    ClipMediaInput,
    ReviewMediaArtifactBuilder,
)

JsonMap = dict[str, object]
JsonRows = list[JsonMap]


class SupportState(BaseModel):
    model_config = ConfigDict(frozen=True)

    tag: str
    label: str
    state: str
    description: str


class StoryChapter(BaseModel):
    model_config = ConfigDict(frozen=True)

    chapter_id: str
    clip_id: str
    label: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    reason: str


class StoryClip(BaseModel):
    model_config = ConfigDict(frozen=True)

    clip_id: str
    label: str
    duration_s: float
    fps: float
    frame_count: int
    raw_detection_count: int
    kept_detection_count: int
    rejected_detection_count: int
    changed_frame_count: int
    source_video_url: str
    raw_overlay_url: str
    adapter_overlay_url: str
    rejected_overlay_url: str
    compare_overlay_url: str
    thumbnail_strip_url: str
    boxes_path: str
    timeline_path: str
    events_path: str
    tracks_path: str
    chapters_path: str


class StoryManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    package_id: str
    workspace_id: str
    default_layout_id: str
    run_suite_id: str
    run_id: str
    experiment_id: str
    status: str
    raw_detection_count: int
    kept_detection_count: int
    rejected_detection_count: int
    interpolated_detection_count: int
    clips: tuple[StoryClip, ...]
    support_states: tuple[SupportState, ...]
    platforms: tuple[JsonMap, ...]


class StoryArtifactBuilder:
    def build(self, run_root: Path, workbench_base_url: str) -> Path:
        manifest = _read_json(run_root / "run-manifest.json")
        clips = tuple(
            _clip_story(run_root, manifest, clip_id)
            for clip_id in _string_tuple(manifest.get("clip_ids"))
        )
        story = StoryManifest(
            package_id=PACKAGE_ID,
            workspace_id=WORKSPACE_ID,
            default_layout_id=DEFAULT_LAYOUT_ID,
            run_suite_id=str(manifest["run_suite_id"]),
            run_id=str(manifest["run_id"]),
            experiment_id=str(manifest["experiment_id"]),
            status="complete",
            raw_detection_count=sum(clip.raw_detection_count for clip in clips),
            kept_detection_count=sum(clip.kept_detection_count for clip in clips),
            rejected_detection_count=sum(clip.rejected_detection_count for clip in clips),
            interpolated_detection_count=0,
            clips=clips,
            support_states=_support_states(),
            platforms=_platform_links(run_root),
        )
        _write_clip_artifacts(run_root, Path(_string_value(manifest.get("data_root"))), clips)
        output = run_root / "review" / "story.json"
        _write_json(
            output,
            story.model_dump(mode="json") | {"workbench_base_url": workbench_base_url},
        )
        return output


def _clip_story(run_root: Path, manifest: JsonMap, clip_id: str) -> StoryClip:
    metadata = _read_json(Path(_string_value(manifest.get("data_root"))) / clip_id / "meta.json")
    hand_boxes = _mapping_value(metadata.get("hand_boxes"))
    detections = _read_rows(run_root / "tables" / f"detections_{clip_id}.parquet")
    decisions = _read_rows(run_root / "tables" / f"decisions_{clip_id}.parquet")
    changed_frames = {
        _int_value(row.get("frame")) for row in decisions if str(row.get("decision")) != "kept"
    }
    decisions_by_kind = Counter(str(row["decision"]) for row in decisions)
    return StoryClip(
        clip_id=clip_id,
        label=_string_value(metadata.get("label"), clip_id),
        duration_s=_float_value(metadata.get("duration_s")),
        fps=_float_value(metadata.get("fps"), 30.0),
        frame_count=_int_value(hand_boxes.get("video_frame_count")),
        raw_detection_count=len(detections),
        kept_detection_count=decisions_by_kind.get("kept", 0),
        rejected_detection_count=len(decisions) - decisions_by_kind.get("kept", 0),
        changed_frame_count=len(changed_frames),
        source_video_url=f"source-video/{clip_id}/left",
        raw_overlay_url=f"review/clips/{clip_id}/{RAW_OVERLAY_FILE}",
        adapter_overlay_url=f"review/clips/{clip_id}/{ADAPTER_OVERLAY_FILE}",
        rejected_overlay_url=f"review/clips/{clip_id}/{REJECTED_OVERLAY_FILE}",
        compare_overlay_url=f"review/clips/{clip_id}/{COMPARE_OVERLAY_FILE}",
        thumbnail_strip_url=f"review/clips/{clip_id}/{THUMBNAIL_STRIP_FILE}",
        boxes_path=f"review/clips/{clip_id}/{BOX_INDEX_FILE}",
        timeline_path=f"review/clips/{clip_id}/timeline.json",
        events_path=f"review/clips/{clip_id}/events.json",
        tracks_path=f"review/clips/{clip_id}/tracks.json",
        chapters_path=f"review/clips/{clip_id}/chapters.json",
    )


def _write_clip_artifacts(run_root: Path, data_root: Path, clips: tuple[StoryClip, ...]) -> None:
    media_builder = ReviewMediaArtifactBuilder()
    for clip in clips:
        clip_root = run_root / "review" / "clips" / clip.clip_id
        detections = _read_rows(run_root / "tables" / f"detections_{clip.clip_id}.parquet")
        decisions = _read_rows(run_root / "tables" / f"decisions_{clip.clip_id}.parquet")
        tracks = _read_rows(run_root / "tables" / f"tracks_{clip.clip_id}.parquet")
        _write_json(clip_root / "events.json", _events(detections, decisions))
        _write_json(clip_root / "tracks.json", _tracks(tracks, detections))
        _write_json(clip_root / "chapters.json", _chapters(clip.clip_id, decisions))
        _write_json(clip_root / "timeline.json", _timeline(clip, decisions, tracks))
        media_builder.build_clip(
            ClipMediaInput(
                run_root=run_root,
                data_root=data_root,
                clip_id=clip.clip_id,
                frame_count=clip.frame_count,
                fps=clip.fps,
            )
        )


def _events(detections: JsonRows, decisions: JsonRows) -> JsonMap:
    detection_by_id = {str(row["detection_id"]): row for row in detections}
    events = [
        _event_row(index, detection_by_id.get(str(decision["detection_id"]), {}), decision)
        for index, decision in enumerate(decisions)
    ]
    return {"events": events}


def _event_row(
    index: int,
    detection: JsonMap,
    decision: JsonMap,
) -> JsonMap:
    return {
        "event_id": f"event-{index:06d}",
        "detection_id": str(decision.get("detection_id")),
        "frame": _int_value(decision.get("frame")),
        "decision": str(decision.get("decision")),
        "stage": str(decision.get("stage")),
        "reason": str(decision.get("reason") or ""),
        "track_id": _optional_int(detection.get("selected_track_id")),
        "confidence": _float_value(detection.get("confidence")),
        "box": _box(detection),
        "display_label": _display_label(decision),
    }


def _tracks(tracks: JsonRows, detections: JsonRows) -> JsonMap:
    frame_by_source = {
        index: _int_value(row.get("frame_index")) for index, row in enumerate(detections)
    }
    grouped: dict[int, JsonRows] = {}
    for row in tracks:
        track_id = _int_value(row.get("track_id"), -1)
        if track_id >= 0:
            grouped.setdefault(track_id, []).append(row)
    return {
        "tracks": [
            _track_row(track_id, rows, frame_by_source) for track_id, rows in grouped.items()
        ]
    }


def _track_row(
    track_id: int,
    rows: JsonRows,
    frame_by_source: dict[int, int],
) -> JsonMap:
    frames = [frame_by_source.get(_int_value(row.get("source_detection_index")), 0) for row in rows]
    return {
        "track_id": track_id,
        "start_frame": min(frames),
        "end_frame": max(frames),
        "duration_frames": max(frames) - min(frames) + 1,
        "observation_count": len(rows),
        "average_confidence": _average(row["track_score"] for row in rows),
        "color_id": track_id % 12,
    }


def _chapters(clip_id: str, decisions: JsonRows) -> JsonMap:
    first_by_reason: dict[str, int] = {}
    for row in decisions:
        reason = str(row.get("reason") or row.get("stage") or "kept")
        if reason and reason not in first_by_reason:
            first_by_reason[reason] = _int_value(row.get("frame"))
    chapters = [
        StoryChapter(
            chapter_id=f"{clip_id}-{reason}",
            clip_id=clip_id,
            label=_customer_label(reason),
            start_frame=max(frame - 45, 0),
            end_frame=frame + 45,
            reason=reason,
        ).model_dump(mode="json")
        for reason, frame in first_by_reason.items()
        if reason != "kept"
    ]
    return {"chapters": chapters}


def _timeline(
    clip: StoryClip,
    decisions: JsonRows,
    tracks: JsonRows,
) -> JsonMap:
    marker_rows = [row for row in decisions if str(row.get("decision")) != "kept"]
    return {
        "clip_id": clip.clip_id,
        "frame_count": clip.frame_count,
        "fps": clip.fps,
        "markers": [_marker(row) for row in marker_rows],
        "track_lanes": sorted(
            {
                _int_value(row.get("track_id"))
                for row in tracks
                if _int_value(row.get("track_id"), -1) >= 0
            }
        ),
    }


def _platform_links(run_root: Path) -> tuple[JsonMap, ...]:
    platforms_path = run_root / "review" / "platforms.json"
    if not platforms_path.exists():
        return ()
    platforms = _read_json(platforms_path)
    return tuple(
        {
            "platform": key,
            "label": _platform_label(key),
            "status": str(value.get("status") or "unknown"),
            "url": value.get("url") if isinstance(value.get("url"), str) else None,
            "path": value.get("path") if isinstance(value.get("path"), str) else None,
            "message": str(value.get("message") or ""),
        }
        for key, value in platforms.items()
        if isinstance(value, dict)
    )


def _platform_label(platform: str) -> str:
    return PLATFORM_LABELS.get(platform, platform.replace("_", " ").title())


def _support_states() -> tuple[SupportState, ...]:
    return tuple(
        SupportState(tag=tag, label=label, state=state, description=description)
        for tag, label, state, description in SUPPORT_ROWS
    )


def _marker(row: JsonMap) -> JsonMap:
    return {
        "frame": _int_value(row.get("frame")),
        "decision": str(row.get("decision")),
        "stage": str(row.get("stage")),
        "reason": str(row.get("reason") or ""),
        "label": _display_label(row),
    }


def _box(detection: JsonMap) -> dict[str, float]:
    return {key: _float_value(detection.get(key)) for key in ("x1", "y1", "x2", "y2")}


def _display_label(row: JsonMap) -> str:
    reason = str(row.get("reason") or row.get("stage") or "kept")
    return _customer_label(reason)


def _customer_label(reason: str) -> str:
    return REASON_LABELS.get(reason, reason.replace("_", " ").title())


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    parsed = _int_value(value, -1)
    return parsed if parsed >= 0 else None


def _average(values: Iterable[object]) -> float:
    numbers = [_float_value(value) for value in values]
    return sum(numbers) / len(numbers) if numbers else 0.0


def _read_rows(path: Path) -> JsonRows:
    rows = pq.read_table(path).to_pylist()
    return cast(JsonRows, rows)


def _read_json(path: Path) -> JsonMap:
    return cast(JsonMap, json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _mapping_value(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value)


def _string_value(value: object, fallback: str = "") -> str:
    return str(value) if value is not None else fallback


def _int_value(value: object, fallback: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    return fallback


def _float_value(value: object, fallback: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return fallback
