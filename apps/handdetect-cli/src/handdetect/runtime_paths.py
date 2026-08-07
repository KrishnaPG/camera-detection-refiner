from __future__ import annotations

import os
import tempfile
from pathlib import Path


def runtime_state_root() -> Path:
    configured_root = os.environ.get("HANDDETECT_TMP_ROOT")
    if configured_root:
        return Path(configured_root)
    return Path(tempfile.gettempdir()) / "handdetect"


def workbench_job_root() -> Path:
    return runtime_state_root() / "workbench" / "jobs"


def replay_root() -> Path:
    return runtime_state_root() / "replays"


def dvclive_root() -> Path:
    return runtime_state_root() / "dvclive"


def mlflow_root() -> Path:
    return runtime_state_root() / "mlruns"
