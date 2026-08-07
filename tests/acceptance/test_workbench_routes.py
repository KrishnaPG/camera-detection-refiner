from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from handdetect.workbench.server import (
    allowed_cors_origins,
    create_app,
    parse_run_ids,
    self_contained_job_script,
    source_video_path,
)

ROOT = Path(__file__).resolve().parents[2]


def test_workbench_index_renders_operator_entrypoints(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HANDDETECT_WORKBENCH_PUBLIC_URL", "http://10.7.0.4:60050")
    monkeypatch.setenv("HANDDETECT_MLFLOW_PUBLIC_URL", "http://10.7.0.4:60900")
    monkeypatch.setenv("HANDDETECT_EVIDENTLY_PUBLIC_URL", "http://10.7.0.4:60904")
    monkeypatch.setenv("HANDDETECT_FIFTYONE_PUBLIC_URL", "http://10.7.0.4:60901")
    monkeypatch.setenv("HANDDETECT_LABEL_STUDIO_PUBLIC_URL", "http://10.7.0.4:60902")
    monkeypatch.setenv("HANDDETECT_CVAT_PUBLIC_URL", "http://10.7.0.4:60903")
    response = TestClient(create_app()).get("/")
    assert response.status_code == 200
    assert "HandDetect Workbench" in response.text
    assert "http://10.7.0.4:60050" in response.text
    assert "http://10.7.0.4:60900" in response.text
    assert "http://10.7.0.4:60904" in response.text
    assert "http://10.7.0.4:60901" in response.text
    assert "http://10.7.0.4:60902" in response.text
    assert "http://10.7.0.4:60903" in response.text
    assert "Run Smoke Experiment" in response.text


def test_workbench_run_detail_renders_platform_links(monkeypatch, tmp_path) -> None:
    suite_id = "suite-20260807-000001"
    run_id = "run-20260807-000001"
    run_root = tmp_path / "runs" / suite_id / run_id
    review_root = run_root / "review"
    review_root.mkdir(parents=True)
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.chdir(tmp_path)

    (run_root / "run-manifest.json").write_text(
        json.dumps({"run_suite_id": suite_id, "run_id": run_id}, indent=2),
        encoding="utf-8",
    )
    (run_root / "evaluation.json").write_text(
        json.dumps({"metrics": {"f1": 0.9}}, indent=2),
        encoding="utf-8",
    )
    (run_root / "regression.json").write_text(
        json.dumps({"baseline": "none", "status": "ok"}, indent=2),
        encoding="utf-8",
    )
    (run_root / "tracking_export_status.json").write_text(
        json.dumps({"mlflow": {"status": "exported"}}, indent=2),
        encoding="utf-8",
    )
    (review_root / "platforms.json").write_text(
        json.dumps(
            {
                "report": {"url": "/artifacts/report/index.html"},
                "mlflow": {"status": "ready", "url": "http://10.7.0.4:60900"},
                "dvc": {"status": "exported", "path": "dvclive/run"},
                "evidently": {"status": "ready", "url": "/artifacts/report/evidently.html"},
                "fiftyone": {"status": "ready", "url": "http://10.7.0.4:60901"},
                "label_studio": {
                    "status": "ready",
                    "url": "/artifacts/review/labelstudio-tasks.json",
                },
                "cvat": {
                    "status": "handoff_ready",
                    "url": "http://10.7.0.4:60903",
                },
                "datumaro": {
                    "status": "handoff_file",
                    "url": "/artifacts/review/datumaro-handoff.json",
                },
                "rerun": {
                    "status": "handoff_file",
                    "url": "/artifacts/review/rerun-handoff.json",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    response = TestClient(create_app()).get(f"/runs/{suite_id}/{run_id}")
    assert response.status_code == 200
    assert f"{suite_id}/{run_id}" in response.text
    assert "Static report" in response.text
    assert "Visual review" in response.text
    assert "Local Story Review" in response.text
    assert f"/artifacts/{suite_id}/{run_id}/report/visual-review.html" in response.text
    assert "http://10.7.0.4:60900" in response.text
    assert "http://10.7.0.4:60901" in response.text
    assert "http://10.7.0.4:60903" in response.text
    assert "Datumaro" in response.text
    assert "Rerun" in response.text
    assert "Open Review Platforms" in response.text
    assert "Replay With Override" in response.text


def test_workbench_story_page_renders_video_review_layout(monkeypatch, tmp_path) -> None:
    suite_id = "suite-20260807-story"
    run_id = "run-20260807-story"
    run_root = tmp_path / "runs" / suite_id / run_id
    review_root = run_root / "review"
    review_root.mkdir(parents=True)
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.chdir(tmp_path)

    (review_root / "story.json").write_text(
        json.dumps(
            {
                "run_suite_id": suite_id,
                "run_id": run_id,
                "status": "complete",
                "default_layout_id": "handdetect_customer_demo_console",
                "raw_detection_count": 10,
                "kept_detection_count": 6,
                "rejected_detection_count": 4,
                "interpolated_detection_count": 0,
                "clips": [
                    {
                        "clip_id": "clip-a",
                        "source_video_url": "review/clips/clip-a/source.mp4",
                        "raw_overlay_url": "review/clips/clip-a/raw_overlay.mp4",
                        "adapter_overlay_url": "review/clips/clip-a/adapter_overlay.mp4",
                        "rejected_overlay_url": "review/clips/clip-a/rejected_overlay.mp4",
                        "compare_overlay_url": "review/clips/clip-a/compare_raw_adapter.mp4",
                        "thumbnail_strip_url": "review/clips/clip-a/thumbnail_strip.webp",
                        "events_path": "review/clips/clip-a/events.json",
                        "timeline_path": "review/clips/clip-a/timeline.json",
                        "tracks_path": "review/clips/clip-a/tracks.json",
                        "chapters_path": "review/clips/clip-a/chapters.json",
                        "boxes_path": "review/clips/clip-a/boxes.json",
                        "label": "fixture",
                        "frame_count": 120,
                        "fps": 30,
                        "raw_detection_count": 10,
                        "kept_detection_count": 6,
                        "rejected_detection_count": 4,
                        "changed_frame_count": 4,
                    }
                ],
                "support_states": [{"label": "Duplicate boxes", "state": "implemented_rejection"}],
                "platforms": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    response = TestClient(create_app()).get(f"/runs/{suite_id}/{run_id}/story")

    assert response.status_code == 200
    assert "RAW DETECTOR" in response.text
    assert "APPROVED HAND TRACKS" in response.text
    assert "Detection Decision" in response.text
    assert "Platform Bridge" in response.text
    assert "rawOverlaySvg" in response.text
    assert "adapterOverlaySvg" in response.text
    assert "zoomSlider" in response.text
    assert "timeContent" in response.text
    assert "clip.raw_overlay_url" in response.text
    assert "clip.adapter_overlay_url" in response.text
    assert "clip.boxes_path" in response.text
    assert "pointerdown" in response.text
    assert "wheel" in response.text


def test_source_video_path_blocks_escape_and_unknown_eye(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    clip_root = data_root / "clip-a"
    clip_root.mkdir(parents=True)
    (clip_root / "video_left.mp4").write_bytes(b"mp4")

    assert source_video_path(data_root, "clip-a", "left") == (clip_root / "video_left.mp4")
    with pytest.raises(HTTPException):
        source_video_path(data_root, "..", "left")
    with pytest.raises(HTTPException):
        source_video_path(data_root, "clip-a", "center")


def test_workbench_review_open_runs_launcher_in_server_process(monkeypatch, tmp_path) -> None:
    suite_id = "suite-20260807-review"
    run_id = "run-20260807-review"
    run_root = tmp_path / "runs" / suite_id / run_id
    run_root.mkdir(parents=True)
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.chdir(ROOT)
    calls: list[dict[str, object]] = []

    (run_root / "run-manifest.json").write_text(
        json.dumps(
            {
                "run_suite_id": suite_id,
                "run_id": run_id,
                "config_path": str(ROOT / "configs" / "smoke-experiment.toml"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    class FakeLauncher:
        def open(self, suite, run, runtime, root):
            calls.append(
                {
                    "suite": str(suite),
                    "run": str(run),
                    "runs_root": runtime.runs_root,
                    "root": root,
                }
            )

    monkeypatch.setattr("handdetect.workbench.server.ReviewJourneyLauncher", FakeLauncher)

    response = TestClient(create_app()).post(
        f"/runs/{suite_id}/{run_id}/review/open",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/runs/{suite_id}/{run_id}"
    assert calls == [
        {
            "suite": suite_id,
            "run": run_id,
            "runs_root": tmp_path / "runs",
            "root": run_root,
        }
    ]


def test_workbench_run_detail_reports_missing_run(monkeypatch, tmp_path) -> None:
    suite_id = "suite-20260807-missing"
    run_id = "run-20260807-missing"
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.chdir(tmp_path)

    response = TestClient(create_app()).get(f"/runs/{suite_id}/{run_id}")

    assert response.status_code == 404
    assert f"Run not found for {suite_id}/{run_id}" in response.text


def test_workbench_artifact_route_reports_missing_file(monkeypatch, tmp_path) -> None:
    suite_id = "suite-20260807-000002"
    run_id = "run-20260807-000002"
    (tmp_path / "runs" / suite_id / run_id).mkdir(parents=True)
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.chdir(tmp_path)

    response = TestClient(create_app()).get(f"/artifacts/{suite_id}/{run_id}/missing.html")

    assert response.status_code == 404
    assert f"Artifact not found for {suite_id}/{run_id}: missing.html" in response.text


def test_workbench_artifact_route_blocks_path_traversal(monkeypatch, tmp_path) -> None:
    suite_id = "suite-20260807-000003"
    run_id = "run-20260807-000003"
    (tmp_path / "runs" / suite_id / run_id).mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(tmp_path / "runs"))
    monkeypatch.chdir(tmp_path)

    response = TestClient(create_app()).get(f"/artifacts/{suite_id}/{run_id}/../../../secret.txt")

    assert response.status_code == 404
    assert "secret" not in response.text


def test_parse_run_ids_only_accepts_success_output_line() -> None:
    suite_id, run_id = parse_run_ids(
        """
        File "/workspace/apps/handdetect-cli/src/handdetect/cli/main.py", line 70, in run
          StaticLineage().capture(parsed.runtime, run_root, suite_id, run_id, config)
        │    85 │   │   │   suite_id=suite_id,
        │    86 │   │   │   run_id=str(run_id),
        """
    )
    assert suite_id is None
    assert run_id is None

    suite_id, run_id = parse_run_ids(
        "suite_id=suite-20260807T044500000000Z "
        "run_id=smoke-acde1234 "
        "report=runs/suite-20260807T044500000000Z/smoke-acde1234/report/index.html"
    )
    assert suite_id == "suite-20260807T044500000000Z"
    assert run_id == "smoke-acde1234"


def test_workbench_job_detail_hides_run_link_for_failed_job(monkeypatch, tmp_path) -> None:
    temp_root = tmp_path / "tmp-state"
    job_root = temp_root / "workbench" / "jobs"
    job_root.mkdir(parents=True)
    job_id = "failed-job"
    log_path = job_root / f"{job_id}.log"
    exit_path = job_root / f"{job_id}.exit"
    meta_path = job_root / f"{job_id}.json"
    log_path.write_text(
        """
        │    85 │   │   │   suite_id=suite_id,
        │    86 │   │   │   run_id=str(run_id),
        FileNotFoundError: [Errno 2] No such file or directory: 'git'
        """.strip(),
        encoding="utf-8",
    )
    exit_path.write_text("1", encoding="utf-8")
    meta_path.write_text(
        json.dumps({"pid": 1234, "log_path": str(log_path), "exit_path": str(exit_path)}, indent=2),
        encoding="utf-8",
    )
    monkeypatch.setenv("HANDDETECT_TMP_ROOT", str(temp_root))
    monkeypatch.chdir(tmp_path)

    response = TestClient(create_app()).get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert "Exit code: 1" in response.text
    assert "No such file or directory" in response.text
    assert "git" in response.text
    assert "Open run" not in response.text


def test_smoke_job_log_reports_public_workbench_url(tmp_path) -> None:
    script = self_contained_job_script(
        tmp_path / "job.log",
        tmp_path / "job.exit",
    )

    assert "HANDDETECT_WORKBENCH_PUBLIC_URL" in script
    assert "public_url" in script
    assert "response.geturl()" not in script


def test_workbench_allows_review_platform_origins(monkeypatch) -> None:
    monkeypatch.setenv("HANDDETECT_WORKBENCH_PUBLIC_URL", "http://10.7.0.4:60050")
    monkeypatch.setenv("HANDDETECT_FIFTYONE_PUBLIC_URL", "http://10.7.0.4:60901")
    monkeypatch.setenv("HANDDETECT_LABEL_STUDIO_PUBLIC_URL", "http://10.7.0.4:60902")

    assert allowed_cors_origins() == [
        "http://10.7.0.4:60050",
        "http://10.7.0.4:60901",
        "http://10.7.0.4:60902",
    ]


def test_runtime_state_root_defaults_to_tmp(monkeypatch) -> None:
    monkeypatch.delenv("HANDDETECT_TMP_ROOT", raising=False)
    from handdetect.runtime_paths import runtime_state_root

    assert str(runtime_state_root()).startswith("/tmp/")
