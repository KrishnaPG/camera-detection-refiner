from __future__ import annotations

import os
from pathlib import Path

import mlflow
from handdetect.tracking_platforms.export_status import PlatformStatus
from handdetect.tracking_platforms.interfaces import TrackingRunSummary


class MlflowExperimentTracker:
    def __init__(self, tracking_uri: str) -> None:
        self.tracking_uri = tracking_uri

    def log_run(self, summary: TrackingRunSummary) -> PlatformStatus:
        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
        os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(str(summary.experiment_id))
        with mlflow.start_run(run_name=str(summary.run_id)) as run:
            mlflow.set_tag("run_suite_id", str(summary.run_suite_id))
            mlflow.set_tag("run_id", str(summary.run_id))
            mlflow.set_tag("config_sha256", summary.config_sha256)
            mlflow.log_param("clip_count", summary.clip_count)
            mlflow.log_param("dataset_file_count", summary.dataset_file_count)
            for metric in summary.metrics:
                mlflow.log_metric(metric.name, metric.value)
            for artifact_path in summary.artifact_paths:
                if artifact_path.exists():
                    mlflow.log_artifact(str(artifact_path))
            run_id = run.info.run_id
        return PlatformStatus(
            status="exported",
            path=str(Path(self.tracking_uri)),
            run_id=run_id,
            url="http://localhost:5000",
        )
