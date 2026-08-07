from __future__ import annotations

import os
from pathlib import Path

from dq_boundaries.config import ExperimentConfigParser
from handdetect_domain.config import ValidatedExperimentConfig


def parse_config_with_runtime_env(config_path: Path) -> ValidatedExperimentConfig:
    parsed = ExperimentConfigParser().parse_path(config_path)
    updates: dict[str, Path | str] = {}
    tmp_root_value = os.environ.get("HANDDETECT_TMP_ROOT", "").strip()
    if tmp_root_value:
        tmp_root = Path(tmp_root_value)
        updates.update(
            {
                "runs_root": tmp_root / "runs",
                "mlflow_tracking_uri": str(tmp_root / "mlruns"),
                "dvclive_root": tmp_root / "dvclive",
                "evidently_root": tmp_root / "evidently",
            }
        )
    env_map = {
        "HANDDETECT_RUNS_ROOT": "runs_root",
        "HANDDETECT_MLFLOW_TRACKING_URI": "mlflow_tracking_uri",
        "HANDDETECT_DVCLIVE_ROOT": "dvclive_root",
        "HANDDETECT_EVIDENTLY_ROOT": "evidently_root",
        "HANDDETECT_WORKBENCH_PUBLIC_URL": "workbench_public_url",
        "HANDDETECT_MLFLOW_PUBLIC_URL": "mlflow_public_url",
        "HANDDETECT_FIFTYONE_PUBLIC_URL": "fiftyone_public_url",
        "HANDDETECT_LABEL_STUDIO_URL": "label_studio_url",
        "HANDDETECT_LABEL_STUDIO_PUBLIC_URL": "label_studio_public_url",
        "HANDDETECT_LABEL_STUDIO_TOKEN": "label_studio_token",
    }
    for env_name, field_name in env_map.items():
        value = os.environ.get(env_name, "").strip()
        if value:
            updates[field_name] = Path(value) if field_name.endswith("_root") else value
    if not updates:
        return parsed
    runtime = parsed.runtime.model_copy(update=updates)
    return parsed.model_copy(update={"runtime": runtime})
