from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path

import pyarrow.parquet as pq
from dq_contracts.ids import RunId, RunSuiteId
from handdetect.review_journey.launcher import ReviewJourneyLauncher
from handdetect_domain.config import RuntimeConfig

ROOT = Path(__file__).resolve().parents[2]


def _run_smoke() -> tuple[str, str]:
    result = subprocess.run(
        ["python", "-m", "handdetect.cli.main", "run", "--config", "configs/smoke-experiment.toml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    suite_id = result.stdout.split("suite_id=", 1)[1].split()[0]
    run_id = result.stdout.split("run_id=", 1)[1].split()[0]
    return suite_id, run_id


def test_tracking_exports_and_review_manifest_are_available() -> None:
    suite_id, run_id = _run_smoke()
    run_root = ROOT / "runs" / suite_id / run_id
    tracking = json.loads((run_root / "tracking_export_status.json").read_text(encoding="utf-8"))
    assert tracking["mlflow"]["status"] == "exported"
    assert tracking["dvc"]["status"] == "exported"
    assert tracking["evidently"]["status"] == "exported"
    review = subprocess.run(
        [
            "python",
            "-m",
            "handdetect.cli.main",
            "review",
            "open",
            "--suite-id",
            suite_id,
            "--run-id",
            run_id,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert review.returncode == 0, review.stderr
    manifest = json.loads((run_root / "review" / "platforms.json").read_text(encoding="utf-8"))
    assert manifest["fiftyone"]["status"] in {"ready", "path_only"}
    assert manifest["label_studio"]["status"] in {"ready", "import_file"}
    report_html = (run_root / "report" / "index.html").read_text(encoding="utf-8")
    assert "Platform manifest: <code>review/platforms.json</code> (available)." in report_html
    assert "not yet generated" not in report_html
    assert "http://localhost:5000" in report_html
    history = pq.read_table(ROOT / "runs" / "index" / "metric_history.parquet").to_pydict()
    assert suite_id in history["run_suite_id"]


def test_lineage_replay_publishes_review_platform_manifest() -> None:
    suite_id, run_id = _run_smoke()
    replay = subprocess.run(
        [
            "python",
            "-m",
            "handdetect.cli.main",
            "lineage",
            "replay",
            "--from-run",
            f"{suite_id}/{run_id}",
            "--set",
            "adapter.max_center_speed_px_per_s=3900.0",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert replay.returncode == 0, replay.stderr
    child_suite = replay.stdout.split("child_suite_id=", 1)[1].split()[0]
    child_run = replay.stdout.split("child_run_id=", 1)[1].split()[0]
    child_root = ROOT / "runs" / child_suite / child_run
    platforms = json.loads((child_root / "review" / "platforms.json").read_text(encoding="utf-8"))
    assert platforms["mlflow"]["status"] == "ready"
    assert platforms["dvc"]["status"] == "ready"
    assert platforms["evidently"]["status"] == "ready"
    assert platforms["fiftyone"]["status"] in {"ready", "path_only"}
    assert platforms["label_studio"]["status"] in {"ready", "import_file"}
    report_html = (child_root / "report" / "index.html").read_text(encoding="utf-8")
    assert "Platform manifest: <code>review/platforms.json</code> (available)." in report_html
    assert "not yet generated" not in report_html
    child_lock = json.loads(
        (child_root / "lineage" / "replay.lock.json").read_text(encoding="utf-8")
    )
    assert child_lock["parent"] == {"run_suite_id": suite_id, "run_id": run_id}


def test_review_launcher_falls_back_when_fiftyone_runtime_breaks(monkeypatch, tmp_path) -> None:
    suite_id = "suite-20260807-000010"
    run_id = "run-20260807-000010"
    run_root = tmp_path / "runs" / suite_id / run_id
    review_root = run_root / "review"
    review_root.mkdir(parents=True)
    (run_root / "run-manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "run_suite_id": suite_id,
                "experiment_id": "smoke",
                "config_sha256": "fixture-config",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_root / "regression.json").write_text(
        json.dumps(
            {
                "passed": True,
                "baseline_available": False,
                "interpolated_detection_count": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_root / "tracking_export_status.json").write_text(
        json.dumps(
            {
                "mlflow": {"status": "exported", "url": None, "path": "mlflow/run"},
                "dvc": {"status": "exported", "path": "dvclive/run"},
                "evidently": {"status": "exported", "path": "report/evidently.html"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (review_root / "fiftyone-dataset.json").write_text(
        json.dumps(
            {
                "dataset_name": "handdetect_suite-20260807-000010_run-20260807-000010",
                "run_suite_id": suite_id,
                "run_id": run_id,
                "samples": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    fake_fiftyone = types.ModuleType("fiftyone")

    class FakeDataset:
        def __init__(self, name: str) -> None:
            self.name = name
            self.persistent = False

        def add_sample(self, sample: object) -> None:
            raise AssertionError(f"unexpected sample: {sample!r}")

        def save(self) -> None:
            return None

    def fake_dataset_exists(dataset_name: str) -> bool:
        return False

    def fake_delete_dataset(dataset_name: str) -> None:
        return None

    def fake_launch_app(
        dataset: FakeDataset,
        address: str,
        port: int,
        remote: bool,
        auto: bool,
    ) -> object:
        raise RuntimeError("mongo backend unavailable")

    fake_fiftyone.Dataset = FakeDataset
    fake_fiftyone.Sample = object
    fake_fiftyone.Detections = object
    fake_fiftyone.Detection = object
    fake_fiftyone.dataset_exists = fake_dataset_exists
    fake_fiftyone.delete_dataset = fake_delete_dataset
    fake_fiftyone.launch_app = fake_launch_app
    monkeypatch.setitem(sys.modules, "fiftyone", fake_fiftyone)
    monkeypatch.chdir(tmp_path)

    runtime = RuntimeConfig(
        data_root=tmp_path / "data",
        runs_root=tmp_path / "runs",
        max_clip_workers=1,
        mlflow_tracking_uri="http://localhost:5000",
        dvclive_root=tmp_path / "dvclive",
        evidently_root=tmp_path / "evidently",
        workbench_host="127.0.0.1",
        workbench_port=8000,
    )

    manifest = ReviewJourneyLauncher().open(RunSuiteId(suite_id), RunId(run_id), runtime, run_root)

    assert manifest.fiftyone.status == "path_only"
    assert manifest.fiftyone.url is None
    platforms = json.loads((review_root / "platforms.json").read_text(encoding="utf-8"))
    assert platforms["fiftyone"]["status"] == "path_only"
    assert platforms["fiftyone"]["url"] is None
