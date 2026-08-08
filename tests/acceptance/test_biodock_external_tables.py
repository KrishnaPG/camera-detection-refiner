from __future__ import annotations

import json
from pathlib import Path

from handdetect.review.biodock_external_tables import (
    HANDDETECT_STORY_ROWS_TABLE,
    BiodockExternalTableArtifactPublisher,
)


def test_biodock_external_table_export_writes_run_partition_without_overwriting(tmp_path) -> None:
    run_root = _run_root(tmp_path, "suite-a", "run-a")
    _write_story(run_root)
    external_root = tmp_path / "berg10" / "external_tables"

    publication = BiodockExternalTableArtifactPublisher().write_story_rows(
        run_root,
        external_root,
    )

    assert publication.source.raw_locator == "handdetect/story_rows/*.jsonl"
    assert publication.source.registration_id == "external-source:handdetect:story-rows"
    assert publication.table.display_name == HANDDETECT_STORY_ROWS_TABLE
    assert publication.table.relative_pattern == publication.source.raw_locator
    assert publication.table.source_registration_id == publication.source.registration_id
    assert publication.row_count == 5

    rows_path = external_root / "handdetect" / "story_rows" / "suite-a--run-a.jsonl"
    assert publication.rows_path == rows_path
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]
    assert {row["event_type"] for row in rows} >= {
        "story_ready",
        "clip_summary",
        "adapter_decision",
        "mot_track_summary",
        "platform_link",
    }
    assert all(row["run_suite_id"] == "suite-a" for row in rows)
    assert all(row["run_id"] == "run-a" for row in rows)
    assert any(row["reason"] == "duplicate_overlap" for row in rows)
    assert any(row["track_id"] == 7 for row in rows)

    other_run_root = _run_root(tmp_path, "suite-a", "run-b")
    _write_story(other_run_root, run_id="run-b")
    BiodockExternalTableArtifactPublisher().write_story_rows(other_run_root, external_root)

    assert rows_path.exists()
    second_rows_path = external_root / "handdetect" / "story_rows" / "suite-a--run-b.jsonl"
    assert second_rows_path.exists()


def _run_root(tmp_path: Path, suite_id: str, run_id: str) -> Path:
    run_root = tmp_path / "runs" / suite_id / run_id
    (run_root / "review" / "clips" / "clip-a").mkdir(parents=True)
    return run_root


def _write_story(run_root: Path, *, run_id: str = "run-a") -> None:
    story = {
        "package_id": "handdetect_quality_adapter",
        "workspace_id": "handdetect_quality_story",
        "default_layout_id": "handdetect_customer_demo_console",
        "run_suite_id": "suite-a",
        "run_id": run_id,
        "experiment_id": "smoke",
        "status": "complete",
        "raw_detection_count": 3,
        "kept_detection_count": 2,
        "rejected_detection_count": 1,
        "interpolated_detection_count": 0,
        "clips": [
            {
                "clip_id": "clip-a",
                "label": "Clip A",
                "duration_s": 2.0,
                "fps": 30.0,
                "frame_count": 60,
                "raw_detection_count": 3,
                "kept_detection_count": 2,
                "rejected_detection_count": 1,
                "changed_frame_count": 1,
                "source_video_url": "source-video/clip-a/left",
                "raw_overlay_url": "review/clips/clip-a/raw_overlay.mp4",
                "adapter_overlay_url": "review/clips/clip-a/adapter_overlay.mp4",
                "rejected_overlay_url": "review/clips/clip-a/rejected_overlay.mp4",
                "compare_overlay_url": "review/clips/clip-a/compare_raw_adapter.mp4",
                "thumbnail_strip_url": "review/clips/clip-a/thumbnail_strip.webp",
                "boxes_path": "review/clips/clip-a/boxes.json",
                "timeline_path": "review/clips/clip-a/timeline.json",
                "events_path": "review/clips/clip-a/events.json",
                "tracks_path": "review/clips/clip-a/tracks.json",
                "chapters_path": "review/clips/clip-a/chapters.json",
            }
        ],
        "support_states": [],
        "platforms": [
            {
                "platform": "fiftyone",
                "label": "FiftyOne",
                "status": "ready",
                "url": "http://10.7.0.4:60901",
                "path": None,
                "message": "Dataset published",
            }
        ],
    }
    clip_root = run_root / "review" / "clips" / "clip-a"
    (run_root / "review" / "story.json").write_text(json.dumps(story), encoding="utf-8")
    (clip_root / "events.json").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "event_id": "event-000001",
                        "detection_id": "det-1",
                        "frame": 12,
                        "decision": "rejected",
                        "stage": "duplicate_filter",
                        "reason": "duplicate_overlap",
                        "track_id": 7,
                        "confidence": 0.92,
                        "display_label": "Duplicate Detections",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (clip_root / "tracks.json").write_text(
        json.dumps(
            {
                "tracks": [
                    {
                        "track_id": 7,
                        "start_frame": 10,
                        "end_frame": 20,
                        "duration_frames": 11,
                        "observation_count": 3,
                        "average_confidence": 0.9,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (clip_root / "timeline.json").write_text(
        json.dumps({"markers": [], "track_lanes": [7]}),
        encoding="utf-8",
    )
