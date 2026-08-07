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


def test_verify_runs_typecheck_gate() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "typecheck:" in makefile
    assert "verify: check typecheck test" in makefile


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


def test_config_runtime_roots_follow_tmp_root_env(monkeypatch, tmp_path: Path) -> None:
    from handdetect.runtime_config import parse_config_with_runtime_env

    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("HANDDETECT_TMP_ROOT", str(runtime_root))

    parsed = parse_config_with_runtime_env(ROOT / "configs" / "smoke-experiment.toml")

    assert parsed.runtime.runs_root == runtime_root / "runs"
    assert parsed.runtime.mlflow_tracking_uri == str(runtime_root / "mlruns")
    assert parsed.runtime.dvclive_root == runtime_root / "dvclive"
    assert parsed.runtime.evidently_root == runtime_root / "evidently"


def test_config_specific_runtime_roots_override_tmp_root_env(monkeypatch, tmp_path: Path) -> None:
    from handdetect.runtime_config import parse_config_with_runtime_env

    runtime_root = tmp_path / "runtime"
    explicit_runs_root = tmp_path / "explicit-runs"
    monkeypatch.setenv("HANDDETECT_TMP_ROOT", str(runtime_root))
    monkeypatch.setenv("HANDDETECT_RUNS_ROOT", str(explicit_runs_root))

    parsed = parse_config_with_runtime_env(ROOT / "configs" / "smoke-experiment.toml")

    assert parsed.runtime.runs_root == explicit_runs_root
    assert parsed.runtime.dvclive_root == runtime_root / "dvclive"
