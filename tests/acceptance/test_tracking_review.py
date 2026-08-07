from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from dq_contracts.ids import RunId, RunSuiteId
from handdetect.review.fiftyone_dataset import FiftyOneDatasetPublisher
from handdetect.review.labelstudio_client import LabelStudioPublisher
from handdetect.review_journey.launcher import ReviewJourneyLauncher
from handdetect.runtime_paths import runs_root
from handdetect.tracking_platforms.evidently_report import EvidentlyReportWriter
from handdetect.tracking_platforms.interfaces import TrackingMetric, TrackingRunSummary
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
    run_root = runs_root() / suite_id / run_id
    tracking = json.loads((run_root / "tracking_export_status.json").read_text(encoding="utf-8"))
    assert tracking["mlflow"]["status"] == "exported"
    assert tracking["dvc"]["status"] == "exported"
    assert tracking["dvc"]["mode"] == "dvclive_metrics_only"
    assert tracking["dvc"]["restore_authority"] is False
    assert tracking["evidently"]["status"] == "exported"
    evidently_path = Path(tracking["evidently"]["path"])
    assert evidently_path.exists()
    assert evidently_path.stat().st_size > 0
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
    assert "DVCLive metrics only" in manifest["dvc"]["message"]
    label_tasks = json.loads((run_root / "review" / "labelstudio-tasks.json").read_text())
    assert label_tasks[0]["predictions"][0]["result"]
    report_html = (run_root / "report" / "index.html").read_text(encoding="utf-8")
    assert "Platform manifest: <code>review/platforms.json</code> (available)." in report_html
    assert (
        "DVCLive metrics only; restore authority remains content-hash snapshot replay."
        in report_html
    )
    assert "not yet generated" not in report_html
    assert "http://localhost:5000" in report_html
    history = pq.read_table(runs_root() / "index" / "metric_history.parquet").to_pydict()
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
    child_root = runs_root() / child_suite / child_run
    platforms = json.loads((child_root / "review" / "platforms.json").read_text(encoding="utf-8"))
    assert platforms["mlflow"]["status"] == "ready"
    assert platforms["dvc"]["status"] == "ready"
    assert "DVCLive metrics only" in platforms["dvc"]["message"]
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
    assert child_lock["restore_authority"] == "content_snapshot"


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


def test_fiftyone_publish_handles_decisions_without_frame_column(monkeypatch, tmp_path) -> None:
    run_root = tmp_path / "runs" / "suite-a" / "run-a"
    (run_root / "review").mkdir(parents=True)
    (run_root / "report" / "samples").mkdir(parents=True)
    (run_root / "tables").mkdir(parents=True)
    image_path = run_root / "report" / "samples" / "sample-000.jpg"
    import cv2

    cv2.imwrite(str(image_path), np.full((8, 8, 3), 255, dtype=np.uint8))
    (run_root / "review" / "fiftyone-dataset.json").write_text(
        json.dumps(
            {
                "dataset_name": "handdetect_suite-a_run-a",
                "samples": [{"clip_id": "clip-1", "frame": 0, "image_name": "sample-000.jpg"}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    pq.write_table(
        pa.table(
            {
                "clip_id": ["clip-1"],
                "detection_id": ["det-1"],
                "frame_index": [0],
                "x1": [1.0],
                "y1": [1.0],
                "x2": [7.0],
                "y2": [7.0],
                "confidence": [0.9],
                "selected": [True],
            }
        ),
        run_root / "tables" / "detections_clip-1.parquet",
    )
    pq.write_table(
        pa.table(
            {
                "clip_id": ["clip-1"],
                "detection_id": ["det-1"],
                "decision": ["kept"],
                "stage": ["max_two_selector"],
                "reason": [""],
            }
        ),
        run_root / "tables" / "decisions_clip-1.parquet",
    )
    fake_fiftyone = _fake_fiftyone_module()
    monkeypatch.setitem(sys.modules, "fiftyone", fake_fiftyone)

    dataset_name, url, error = FiftyOneDatasetPublisher().publish(
        RunSuiteId("suite-a"),
        RunId("run-a"),
        run_root,
    )

    assert dataset_name == "handdetect_suite-a_run-a"
    assert url == "http://localhost:5151"
    assert error is None
    dataset = fake_fiftyone._datasets[dataset_name]
    assert len(dataset.samples) == 1
    assert len(dataset.samples[0]["cleaned"].detections) == 1


def test_evidently_writer_uses_package_api_when_available(monkeypatch, tmp_path) -> None:
    run_root = tmp_path / "runs" / "suite-a" / "run-a"
    (run_root / "report").mkdir(parents=True)
    fake_evidently = _fake_evidently_module()
    monkeypatch.setitem(sys.modules, "evidently", fake_evidently)
    monkeypatch.setitem(sys.modules, "evidently.presets", fake_evidently.presets)
    summary = TrackingRunSummary(
        run_suite_id=RunSuiteId("suite-a"),
        run_id=RunId("run-a"),
        experiment_id="smoke",
        config_sha256="cfg",
        dataset_file_count=1,
        clip_count=1,
        metrics=(TrackingMetric(name="raw_detection_count", value=3.0),),
        artifact_paths=(),
        run_root=run_root,
    )

    status = EvidentlyReportWriter().write(summary)

    assert status.status == "exported"
    assert (run_root / "report" / "evidently.html").read_text(encoding="utf-8") == "evidently-html"


def test_evidently_writer_degrades_when_package_api_fails(monkeypatch, tmp_path) -> None:
    run_root = tmp_path / "runs" / "suite-a" / "run-a"
    (run_root / "report").mkdir(parents=True)
    fake_evidently = _fake_evidently_module(raise_on_run=True)
    monkeypatch.setitem(sys.modules, "evidently", fake_evidently)
    monkeypatch.setitem(sys.modules, "evidently.presets", fake_evidently.presets)
    summary = TrackingRunSummary(
        run_suite_id=RunSuiteId("suite-a"),
        run_id=RunId("run-a"),
        experiment_id="smoke",
        config_sha256="cfg",
        dataset_file_count=1,
        clip_count=1,
        metrics=(TrackingMetric(name="raw_detection_count", value=3.0),),
        artifact_paths=(),
        run_root=run_root,
    )

    status = EvidentlyReportWriter().write(summary)

    assert status.status == "degraded"
    assert status.error is not None
    assert "api failure" in status.error


def test_label_studio_publish_reuses_existing_import_manifest(monkeypatch, tmp_path) -> None:
    run_root = tmp_path / "runs" / "suite-a" / "run-a"
    (run_root / "review").mkdir(parents=True)
    (run_root / "review" / "labelstudio-tasks.json").write_text("[]", encoding="utf-8")
    (run_root / "review" / "labelstudio-import.json").write_text(
        json.dumps(
            {
                "project_id": 17,
                "url": "http://labelstudio/projects/17",
                "imported_task_count": 3,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    def fail_client(*args, **kwargs):
        raise AssertionError("client should not be constructed when manifest exists")

    monkeypatch.setattr("handdetect.review.labelstudio_client.Client", fail_client)

    project_id, imported = LabelStudioPublisher().publish(run_root, "http://labelstudio", "token")

    assert project_id == 17
    assert imported == 3


def _fake_fiftyone_module() -> types.ModuleType:
    fake = types.ModuleType("fiftyone")
    fake._datasets = {}

    class FakeDataset:
        def __init__(self, name: str) -> None:
            self.name = name
            self.samples: list[FakeSample] = []
            self.persistent = False
            fake._datasets[name] = self

        def add_sample(self, sample: FakeSample) -> None:
            self.samples.append(sample)

        def save(self) -> None:
            return None

    class FakeSample(dict):
        def __init__(self, filepath: str) -> None:
            super().__init__()
            self.filepath = filepath

    class FakeDetections:
        def __init__(self, detections: list[object]) -> None:
            self.detections = detections

    class FakeDetection(dict):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)

    class FakeSession:
        server_port = 5151

    fake.Dataset = FakeDataset
    fake.Sample = FakeSample
    fake.Detections = FakeDetections
    fake.Detection = FakeDetection
    fake.dataset_exists = lambda name: False
    fake.delete_dataset = lambda name: None
    fake.launch_app = lambda dataset, address, port, remote, auto: FakeSession()
    return fake


def _fake_evidently_module(*, raise_on_run: bool = False) -> types.ModuleType:
    fake = types.ModuleType("evidently")
    presets = types.ModuleType("evidently.presets")

    class FakePreset:
        pass

    class FakeSnapshot:
        def save_html(self, path: str | Path) -> None:
            Path(path).write_text("evidently-html", encoding="utf-8")

    class FakeReport:
        def __init__(self, metrics: list[object]) -> None:
            self.metrics = metrics

        def run(self, **kwargs):
            if raise_on_run:
                raise RuntimeError("api failure")
            return FakeSnapshot()

    presets.DataSummaryPreset = FakePreset
    fake.Report = FakeReport
    fake.presets = presets
    return fake
