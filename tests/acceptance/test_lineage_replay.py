from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import tomlkit
from handdetect.lineage.replay import LineageReplayService
from handdetect.runtime_paths import runs_root

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


def test_lineage_replay_creates_child_run_without_overwriting_parent() -> None:
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
    parent_root = runs_root() / suite_id / run_id
    child_root = runs_root() / child_suite / child_run
    assert parent_root.exists()
    assert child_root.exists()
    child_lock = json.loads(
        (child_root / "lineage" / "replay.lock.json").read_text(encoding="utf-8")
    )
    assert child_lock["parent"]["run_suite_id"] == suite_id
    assert child_lock["parent"]["run_id"] == run_id


def test_lineage_replay_uses_restored_worktree_inputs_and_main_run_roots(
    monkeypatch,
    tmp_path,
) -> None:
    repo_root, _ = _build_replay_fixture(tmp_path)
    commands: list[tuple[tuple[str, ...], Path | None]] = []
    child_suite = "suite-child"
    child_run = "run-child"

    def fake_run(
        command: list[str],
        *,
        cwd: Path | None = None,
        check: bool,
        text: bool,
        capture_output: bool = False,
    ):
        del check, text
        commands.append((tuple(command), cwd))
        if command[:3] == ["git", "worktree", "add"]:
            Path(command[4]).mkdir(parents=True, exist_ok=True)
            return _Completed(stdout="")
        if command[:2] == ["git", "apply"]:
            return _Completed(stdout="")
        if command[:3] == ["python", "-m", "handdetect.cli.main"]:
            config_path = Path(command[-1])
            document = tomlkit.parse(config_path.read_text(encoding="utf-8"))
            runtime = document["runtime"]
            assert Path(str(runtime["data_root"])) == cwd / "data"
            assert Path(str(runtime["runs_root"])) == repo_root / "runs"
            assert Path(str(runtime["evidently_root"])) == repo_root / "runs" / "evidently"
            assert str(runtime["mlflow_tracking_uri"]).endswith("/mlruns")
            assert Path(str(runtime["dvclive_root"])).name == "dvclive"
            assert str(runtime["label_studio_url"]) == "http://labelstudio.internal"
            assert str(runtime["label_studio_public_url"]) == "http://localhost:8080"
            assert str(runtime["label_studio_token"]) == "token"
            assert document["experiments"][0]["adapter"]["max_center_speed_px_per_s"] == 3900.0
            child_lock = (
                repo_root / "runs" / child_suite / child_run / "lineage" / "replay.lock.json"
            )
            child_lock.parent.mkdir(parents=True, exist_ok=True)
            child_lock.write_text(
                json.dumps({"run_suite_id": child_suite, "run_id": child_run}, indent=2),
                encoding="utf-8",
            )
            _write_evaluation(repo_root / "runs" / child_suite / child_run)
            _write_child_run_artifacts(
                repo_root / "runs" / child_suite / child_run,
                child_suite,
                child_run,
                "smoke",
            )
            return _Completed(stdout=f"suite_id={child_suite} run_id={child_run}\n")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("HANDDETECT_TMP_ROOT", str(tmp_path / "tmp-root"))
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(repo_root / "runs"))
    monkeypatch.setenv("HANDDETECT_LABEL_STUDIO_URL", "http://labelstudio.internal")
    monkeypatch.setenv("HANDDETECT_LABEL_STUDIO_PUBLIC_URL", "http://localhost:8080")
    monkeypatch.setenv("HANDDETECT_LABEL_STUDIO_TOKEN", "token")
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(LineageReplayService, "_replay_id", lambda self: "replay-001")
    monkeypatch.setattr(
        LineageReplayService,
        "_publish_child_review",
        lambda self, suite_id, run_id, config_path: None,
    )

    result = LineageReplayService().replay(
        "suite-parent/run-parent",
        ["adapter.max_center_speed_px_per_s=3900.0"],
    )

    assert result == (child_suite, child_run)
    replay_status = json.loads(
        (tmp_path / "tmp-root" / "replays" / "replay-001" / "replay-status.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[-1]
    )
    assert replay_status["restore"]["mode"] == "content_snapshot"
    assert replay_status["restore"]["used_dvc_checkout"] is False
    assert replay_status["restore"]["restore_authority"] == "content_snapshot"
    assert replay_status["child_suite_id"] == child_suite
    assert replay_status["child_run_id"] == child_run
    child_lock = json.loads(
        (repo_root / "runs" / child_suite / child_run / "lineage" / "replay.lock.json").read_text(
            encoding="utf-8"
        )
    )
    assert child_lock["parent"] == {"run_suite_id": "suite-parent", "run_id": "run-parent"}
    comparison = json.loads(
        (
            repo_root / "runs" / child_suite / child_run / "lineage" / "parent-comparison.json"
        ).read_text(encoding="utf-8")
    )
    assert comparison["parent_run_root"] == str(repo_root / "runs" / "suite-parent" / "run-parent")
    assert all(command[0][0] != "dvc" for command in commands)


def test_lineage_replay_targets_parent_experiment_and_preserves_override_types(
    monkeypatch,
    tmp_path,
) -> None:
    repo_root, _ = _build_replay_fixture(
        tmp_path,
        config_text=_multi_experiment_config_text(),
        parent_experiment_id="strict_speed",
    )

    def fake_run(
        command: list[str],
        *,
        cwd: Path | None = None,
        check: bool,
        text: bool,
        capture_output: bool = False,
    ):
        del check, text, capture_output
        if command[:3] == ["git", "worktree", "add"]:
            Path(command[4]).mkdir(parents=True, exist_ok=True)
            return _Completed(stdout="")
        if command[:2] == ["git", "apply"]:
            return _Completed(stdout="")
        if command[:3] == ["python", "-m", "handdetect.cli.main"]:
            config_path = Path(command[-1])
            document = tomlkit.parse(config_path.read_text(encoding="utf-8"))
            assert str(document["runtime"]["label_studio_url"]) == "http://labelstudio.internal"
            baseline = document["experiments"][0]
            strict_speed = document["experiments"][1]
            assert str(baseline["name"]) == "baseline"
            assert baseline["bytetrack"]["lost_track_buffer"] == 2
            assert list(baseline["enabled_filters"]) == ["geometric"]
            assert str(strict_speed["name"]) == "strict_speed"
            assert strict_speed["bytetrack"]["lost_track_buffer"] == 7
            assert list(strict_speed["enabled_filters"]) == ["tracking", "temporal", "max_two"]
            child_run = "strict_speed-bbb"
            child_lock = (
                repo_root / "runs" / "suite-child" / child_run / "lineage" / "replay.lock.json"
            )
            child_lock.parent.mkdir(parents=True, exist_ok=True)
            child_lock.write_text("{}", encoding="utf-8")
            _write_evaluation(repo_root / "runs" / "suite-child" / child_run)
            _write_child_run_artifacts(
                repo_root / "runs" / "suite-child" / child_run,
                "suite-child",
                child_run,
                "strict_speed",
            )
            return _Completed(
                stdout=(
                    "suite_id=suite-child run_id=baseline-aaa\n"
                    "suite_id=suite-child run_id=strict_speed-bbb\n"
                )
            )
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("HANDDETECT_TMP_ROOT", str(tmp_path / "tmp-root"))
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(repo_root / "runs"))
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(LineageReplayService, "_replay_id", lambda self: "replay-typed-001")
    monkeypatch.setattr(
        LineageReplayService,
        "_publish_child_review",
        lambda self, suite_id, run_id, config_path: None,
    )

    result = LineageReplayService().replay(
        "suite-parent/run-parent",
        [
            'runtime.label_studio_url="http://labelstudio.internal"',
            "bytetrack.lost_track_buffer=7",
            'enabled_filters=["tracking", "temporal", "max_two"]',
        ],
    )

    assert result == ("suite-child", "strict_speed-bbb")


def test_lineage_replay_runs_dvc_restore_when_metadata_is_present(monkeypatch, tmp_path) -> None:
    repo_root, _ = _build_replay_fixture(tmp_path, include_dvc_metadata=True)
    commands: list[tuple[tuple[str, ...], Path | None]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path | None = None,
        check: bool,
        text: bool,
        capture_output: bool = False,
    ):
        del check, text, capture_output
        commands.append((tuple(command), cwd))
        if command[:3] == ["git", "worktree", "add"]:
            Path(command[4]).mkdir(parents=True, exist_ok=True)
            return _Completed(stdout="")
        if command[:2] == ["git", "apply"]:
            return _Completed(stdout="")
        if command[0] == "dvc":
            return _Completed(stdout="")
        if command[:3] == ["python", "-m", "handdetect.cli.main"]:
            child_lock = (
                repo_root / "runs" / "suite-child" / "run-child" / "lineage" / "replay.lock.json"
            )
            child_lock.parent.mkdir(parents=True, exist_ok=True)
            child_lock.write_text("{}", encoding="utf-8")
            _write_evaluation(repo_root / "runs" / "suite-child" / "run-child")
            _write_child_run_artifacts(
                repo_root / "runs" / "suite-child" / "run-child",
                "suite-child",
                "run-child",
                "smoke",
            )
            return _Completed(stdout="suite_id=suite-child run_id=run-child\n")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("HANDDETECT_TMP_ROOT", str(tmp_path / "tmp-root"))
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(repo_root / "runs"))
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(LineageReplayService, "_replay_id", lambda self: "replay-002")
    monkeypatch.setattr(
        LineageReplayService,
        "_publish_child_review",
        lambda self, suite_id, run_id, config_path: None,
    )

    LineageReplayService().replay("suite-parent/run-parent", [])

    dvc_commands = [command for command in commands if command[0][0] == "dvc"]
    assert [command[0] for command in dvc_commands] == [
        ("dvc", "pull"),
        ("dvc", "checkout"),
    ]
    replay_status = json.loads(
        (tmp_path / "tmp-root" / "replays" / "replay-002" / "replay-status.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[-1]
    )
    assert replay_status["restore"]["mode"] == "content_snapshot"
    assert replay_status["restore"]["used_dvc_checkout"] is True
    assert replay_status["restore"]["restore_authority"] == "content_snapshot"


class _Completed:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def _build_replay_fixture(
    tmp_path: Path,
    *,
    include_dvc_metadata: bool = False,
    config_text: str | None = None,
    parent_experiment_id: str = "smoke",
) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    run_root = repo_root / "runs" / "suite-parent" / "run-parent"
    lineage_root = run_root / "lineage"
    snapshot_root = lineage_root / "source-snapshot"
    config_path = repo_root / "configs" / "parent.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        config_text
        or """
[runtime]
data_root = "data"
runs_root = "runs"
max_clip_workers = 1
mlflow_tracking_uri = "mlruns"
dvclive_root = "dvclive"
evidently_root = "runs/evidently"

[[experiments]]
name = "smoke"
enabled_filters = []

[experiments.adapter]
duplicate_iou_threshold = 0.5
min_box_area_px = 1.0
max_box_area_px = 10.0
min_aspect_ratio = 0.1
max_aspect_ratio = 10.0
max_center_speed_px_per_s = 1200.0
min_track_length_frames = 1
static_camera_motion_px = 1.0
static_box_motion_px = 1.0

[experiments.bytetrack]
track_activation_threshold = 0.5
minimum_matching_threshold = 0.5
lost_track_buffer = 2
frame_rate = 30
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (snapshot_root / "configs").mkdir(parents=True, exist_ok=True)
    (snapshot_root / "data").mkdir(parents=True, exist_ok=True)
    (snapshot_root / "labels" / "versions" / "empty-gold-v1").mkdir(parents=True, exist_ok=True)
    (snapshot_root / "configs" / "parent.toml").write_text(
        config_path.read_text(encoding="utf-8").replace("1200.0", "2200.0"),
        encoding="utf-8",
    )
    (snapshot_root / "data" / "from-snapshot.txt").write_text("snapshot", encoding="utf-8")
    if include_dvc_metadata:
        (snapshot_root / "dvc.yaml").write_text("stages: {}\n", encoding="utf-8")
    lineage_root.mkdir(parents=True, exist_ok=True)
    (run_root / "run-manifest.json").write_text(
        json.dumps(
            {"config_path": "configs/parent.toml", "experiment_id": parent_experiment_id},
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_evaluation(run_root)
    data_hash = _tree_hash(snapshot_root / "data")
    labels_hash = _tree_hash(snapshot_root / "labels" / "versions" / "empty-gold-v1")
    config_hash = _file_hash(snapshot_root / "configs" / "parent.toml")
    (lineage_root / "replay.lock.json").write_text(
        json.dumps(
            {
                "git": {"commit_sha": "abc123"},
                "dataset": {"path": "data", "content_sha256": data_hash},
                "labels": {
                    "path": "labels/versions/empty-gold-v1",
                    "content_sha256": labels_hash,
                },
                "config": {"path": "configs/parent.toml", "content_sha256": config_hash},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return repo_root, run_root


def _write_evaluation(run_root: Path) -> None:
    (run_root / "evaluation.json").write_text(
        json.dumps(
            {
                "raw_detection_count": 1,
                "cleaned_detection_count": 1,
                "rejected_detection_count": 0,
                "interpolated_detection_count": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_child_run_artifacts(
    run_root: Path,
    suite_id: str,
    run_id: str,
    experiment_id: str,
) -> None:
    (run_root / "run-manifest.json").write_text(
        json.dumps(
            {
                "run_suite_id": suite_id,
                "run_id": run_id,
                "experiment_id": experiment_id,
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
                "baseline_available": True,
                "interpolated_detection_count": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hash(root: Path) -> str:
    hasher = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        hasher.update(str(path.relative_to(root)).encode("utf-8"))
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _multi_experiment_config_text() -> str:
    return (
        """
[runtime]
data_root = "data"
runs_root = "runs"
max_clip_workers = 1
mlflow_tracking_uri = "mlruns"
dvclive_root = "dvclive"
evidently_root = "runs/evidently"

[[experiments]]
name = "baseline"
enabled_filters = ["geometric"]

[experiments.adapter]
duplicate_iou_threshold = 0.5
min_box_area_px = 1.0
max_box_area_px = 10.0
min_aspect_ratio = 0.1
max_aspect_ratio = 10.0
max_center_speed_px_per_s = 1200.0
min_track_length_frames = 1
static_camera_motion_px = 1.0
static_box_motion_px = 1.0

[experiments.bytetrack]
track_activation_threshold = 0.5
minimum_matching_threshold = 0.5
lost_track_buffer = 2
frame_rate = 30

[[experiments]]
name = "strict_speed"
enabled_filters = ["geometric"]

[experiments.adapter]
duplicate_iou_threshold = 0.5
min_box_area_px = 1.0
max_box_area_px = 10.0
min_aspect_ratio = 0.1
max_aspect_ratio = 10.0
max_center_speed_px_per_s = 2200.0
min_track_length_frames = 1
static_camera_motion_px = 1.0
static_box_motion_px = 1.0

[experiments.bytetrack]
track_activation_threshold = 0.5
minimum_matching_threshold = 0.5
lost_track_buffer = 4
frame_rate = 30
""".strip()
        + "\n"
    )
