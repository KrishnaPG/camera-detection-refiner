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


def test_run_smoke_writes_cleaned_and_audit_artifacts() -> None:
    suite_id, run_id = _run_smoke()
    run_root = ROOT / "runs" / suite_id / run_id
    cleaned = sorted((run_root / "cleaned").glob("*.json"))
    audit = sorted((run_root / "audit").glob("*.jsonl"))
    assert cleaned
    assert audit
    payload = json.loads(cleaned[0].read_text(encoding="utf-8"))
    assert payload["interpolated_detection_count"] == 0
    assert payload["max_detections_per_frame"] <= 2
