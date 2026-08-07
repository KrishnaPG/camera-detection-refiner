from __future__ import annotations

import json

from fastapi.testclient import TestClient
from handdetect.workbench.server import create_app, parse_run_ids


def test_workbench_index_renders_operator_entrypoints(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    response = TestClient(create_app()).get("/")
    assert response.status_code == 200
    assert "HandDetect Workbench" in response.text
    assert "http://localhost:8000" in response.text
    assert "http://localhost:5000" in response.text
    assert "http://localhost:5151" in response.text
    assert "http://localhost:8080" in response.text
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
                "mlflow": {"status": "ready", "url": "http://localhost:5000"},
                "dvc": {"status": "exported", "path": "dvclive/run"},
                "evidently": {"status": "ready", "url": "/artifacts/report/evidently.html"},
                "fiftyone": {"status": "ready", "url": "http://localhost:5151"},
                "label_studio": {
                    "status": "ready",
                    "url": "/artifacts/review/labelstudio-tasks.json",
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
    assert "http://localhost:5000" in response.text
    assert "http://localhost:5151" in response.text
    assert "Replay With Override" in response.text


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


def test_runtime_state_root_defaults_to_tmp(monkeypatch) -> None:
    monkeypatch.delenv("HANDDETECT_TMP_ROOT", raising=False)
    from handdetect.runtime_paths import runtime_state_root

    assert str(runtime_state_root()).startswith("/tmp/")
