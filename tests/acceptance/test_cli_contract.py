from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_root_task_interface_exposes_required_targets() -> None:
    result = subprocess.run(
        ["make", "doctor"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "handdetect doctor" in result.stdout


def test_cli_help_lists_public_commands() -> None:
    result = subprocess.run(
        ["python", "-m", "handdetect.cli.main", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    for command in [
        "doctor",
        "seed",
        "run",
        "check",
        "test",
        "verify",
        "migrate",
        "clean",
        "review",
        "lineage",
        "workbench",
    ]:
        assert command in result.stdout


def test_make_clean_removes_isolated_runtime_state(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    tmp_runtime_root = tmp_path / "tmp-state"
    for path in [
        runs_root / "suite-a" / "run-a",
        tmp_runtime_root / "dvclive" / "suite-a",
        tmp_runtime_root / "workbench" / "jobs",
    ]:
        path.mkdir(parents=True, exist_ok=True)
        (path / "marker.txt").write_text("present", encoding="utf-8")

    env = {
        **os.environ,
        "HANDDETECT_RUNS_ROOT": str(runs_root),
        "HANDDETECT_TMP_ROOT": str(tmp_runtime_root),
    }
    result = subprocess.run(
        ["make", f"PYTHON={sys.executable}", "clean"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert f"cleaned={runs_root}" in result.stdout
    assert not runs_root.exists()
    assert not (tmp_runtime_root / "dvclive").exists()
    assert not (tmp_runtime_root / "workbench").exists()
