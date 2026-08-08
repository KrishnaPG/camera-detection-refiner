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
        "HANDDETECT_BIODOCK_PUBLIC_URL": "biodock_public_url",
        "HANDDETECT_BIODOCK_RPC_URL": "biodock_rpc_url",
        "HANDDETECT_BIODOCK_ACCESS_TOKEN": "biodock_access_token",
        "HANDDETECT_BIODOCK_TOKEN_URL": "biodock_token_url",
        "HANDDETECT_BIODOCK_CLIENT_ID": "biodock_client_id",
        "HANDDETECT_BIODOCK_CLIENT_SECRET": "biodock_client_secret",
        "HANDDETECT_BIODOCK_EXTERNAL_TABLE_ROOT": "biodock_external_table_root",
        "HANDDETECT_MLFLOW_PUBLIC_URL": "mlflow_public_url",
        "HANDDETECT_FIFTYONE_PUBLIC_URL": "fiftyone_public_url",
        "HANDDETECT_LABEL_STUDIO_URL": "label_studio_url",
        "HANDDETECT_LABEL_STUDIO_PUBLIC_URL": "label_studio_public_url",
        "HANDDETECT_LABEL_STUDIO_TOKEN": "label_studio_token",
        "HANDDETECT_CVAT_URL": "cvat_url",
        "HANDDETECT_CVAT_PUBLIC_URL": "cvat_public_url",
        "HANDDETECT_CVAT_USERNAME": "cvat_username",
        "HANDDETECT_CVAT_PASSWORD": "cvat_password",
        "HANDDETECT_DATUMARO_URL": "datumaro_url",
        "HANDDETECT_RERUN_PUBLIC_URL": "rerun_public_url",
        "HANDDETECT_EVIDENTLY_PUBLIC_URL": "evidently_public_url",
    }
    for env_name, field_name in env_map.items():
        value = os.environ.get(env_name, "").strip()
        if value:
            updates[field_name] = (
                Path(value)
                if field_name.endswith("_root") or field_name.endswith("_table_root")
                else value
            )
    if not updates:
        return parsed
    runtime = parsed.runtime.model_copy(update=updates)
    return parsed.model_copy(update={"runtime": runtime})
