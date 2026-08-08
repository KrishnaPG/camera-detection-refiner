from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_generator_package_uses_biodock_video_review_layout() -> None:
    workspace = json.loads(
        (ROOT / "generator-package" / "ui" / "workspace.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (ROOT / "generator-package" / "generator-package-manifest.json").read_text(encoding="utf-8")
    )
    raw_schema = json.loads(
        (ROOT / "generator-package" / "schemas" / "handdetect-run-event.schema.json").read_text(
            encoding="utf-8"
        )
    )
    story_schema = json.loads(
        (ROOT / "generator-package" / "schemas" / "handdetect-story-row.schema.json").read_text(
            encoding="utf-8"
        )
    )
    views_sql = (ROOT / "generator-package" / "views" / "handdetect_story_views.sql").read_text(
        encoding="utf-8"
    )
    default_layout = next(
        layout
        for layout in workspace["layouts"]
        if layout["layoutId"] == workspace["defaultLayoutId"]
    )

    assert manifest["metadata"]["package_id"] == "handdetect_quality_adapter"
    assert workspace["workspaceId"] == "handdetect_quality_story"
    assert workspace["theme"]["skinPackId"] == "handdetect-forensic-workbench"
    assert {
        panel["panelId"]: panel["appPanel"] for panel in workspace["panels"]
    }["handdetect_synchronized_viewer"] == "biodock.externalReviewFrame"
    assert default_layout["extends"] == "berg10.generator.videoReview"
    assert default_layout["slots"]["slot.history"] == ["handdetect_timeline"]
    assert "handdetect.run_smoke_experiment" in {
        action["action_id"] for action in manifest["actions"]
    }
    assert set(manifest["raw_admissions"][0]["families"]) <= {
        "a_session_snapshot",
        "a_message_event",
        "a_task_event",
        "a_artifact_event",
        "a_runtime_event",
        "a_intent_event",
        "a_exclusion_event",
        "a_replay_checkpoint",
        "a_backpressure_event",
        "b_session",
        "b_message",
        "b_task",
        "b_artifact",
        "b_artifact_access",
        "b_runtime_status",
        "b_intent",
        "b_exclusion",
        "b_conflict",
        "b_replay_window",
        "b_replay_checkpoint",
        "b_backpressure",
        "b_transform",
    }
    assert raw_schema["x-berg10"]["kind"] == "raw_source_payload"
    assert raw_schema["x-berg10.kind"] == "raw_source_schema"
    assert set(raw_schema["properties"]["family"]["enum"]) == set(
        manifest["raw_admissions"][0]["families"]
    )
    assert story_schema["x-berg10"]["kind"] == "c_view_row"
    assert story_schema["required"] == ["row_id", "run_id"]
    panel_view_ids = {panel["viewId"] for panel in workspace["panels"]}
    annotated_view_ids = {
        line.removeprefix("-- berg10:view id=").strip()
        for line in views_sql.splitlines()
        if line.startswith("-- berg10:view id=")
    }
    assert panel_view_ids <= annotated_view_ids
    assert "schema=schemas/handdetect-story-row.schema.json" in views_sql


def test_generator_package_descriptor_is_sdk_generated() -> None:
    generated_paths = (
        ROOT / "generator-package" / "generator-package-manifest.json",
        ROOT / "generator-package" / "ui" / "workspace.json",
    )
    before = {path: path.read_text(encoding="utf-8") for path in generated_paths}
    result = subprocess.run(
        ["python", "scripts/build_handdetect_generator_package.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    after = {path: path.read_text(encoding="utf-8") for path in generated_paths}
    assert after == before
