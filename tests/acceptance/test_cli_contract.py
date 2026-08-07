from __future__ import annotations

import subprocess
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
