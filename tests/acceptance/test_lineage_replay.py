from __future__ import annotations

import json
import subprocess
from pathlib import Path

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
    parent_root = ROOT / "runs" / suite_id / run_id
    child_root = ROOT / "runs" / child_suite / child_run
    assert parent_root.exists()
    assert child_root.exists()
    child_lock = json.loads(
        (child_root / "lineage" / "replay.lock.json").read_text(encoding="utf-8")
    )
    assert child_lock["parent"]["run_suite_id"] == suite_id
    assert child_lock["parent"]["run_id"] == run_id
