from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dq_contracts.ids import ExperimentId, RunId, RunSuiteId
from handdetect.eval.calibration import CalibrationSweepRunner
from handdetect.eval.metrics import EvaluationRunner
from handdetect.pipeline.clip_runner import ClipRunner
from handdetect.regression.gates import RegressionGateRunner
from handdetect.report.overlays import OverlaySampler
from handdetect.report.sampling import SampleManifestBuilder
from handdetect.report.static_report import StaticReportBuilder
from handdetect.runs.catalog import RunCatalog
from handdetect.runs.ids import RunIdProvider
from handdetect.runs.manifest import RunManifest
from handdetect.runs.retention import RuntimeRetentionPruner
from handdetect.runs.store import RunArtifactStore
from handdetect.tracking_platforms.dvc_tracker import DvcLiveTracker
from handdetect.tracking_platforms.evidently_report import EvidentlyReportWriter
from handdetect.tracking_platforms.export_status import (
    TrackingExportStatus,
    TrackingExportStatusWriter,
)
from handdetect.tracking_platforms.interfaces import TrackingMetric, TrackingRunSummary
from handdetect.tracking_platforms.mlflow_tracker import MlflowExperimentTracker
from handdetect_domain.config import ValidatedExperimentConfig
from handdetect_io.dataset import DatasetScanner


class ExperimentRunner:
    def run(
        self, config: ValidatedExperimentConfig, suite_id: RunSuiteId, config_path: Path
    ) -> list[RunId]:
        config_bytes = config.model_dump_json().encode("utf-8")
        config_hash = hashlib.sha256(config_bytes).hexdigest()
        clips = DatasetScanner().scan(config.runtime.data_root)
        retention = RuntimeRetentionPruner()
        retention.prune_default_runtime()
        catalog = RunCatalog.open(config.runtime.runs_root)
        run_ids: list[RunId] = []

        for experiment in config.experiments:
            run_id = RunIdProvider().create(suite_id, ExperimentId(experiment.name), config_hash)
            store = RunArtifactStore.open(config.runtime.runs_root, suite_id, run_id)
            selected_clips = clips[:3] if experiment.name == "smoke" else clips
            clip_summaries = [
                ClipRunner().run_clip(clip, run_id, experiment, store) for clip in selected_clips
            ]
            manifest = RunManifest(
                run_id=run_id,
                run_suite_id=suite_id,
                experiment_id=ExperimentId(experiment.name),
                data_root=config.runtime.data_root,
                output_root=store.root,
                config_path=config_path,
                clip_ids=tuple(clip.clip_id for clip in selected_clips),
                config_sha256=config_hash,
                code_version="0.1.0",
                label_set_id="empty-gold-v1",
            )
            (store.root / "run-manifest.json").write_text(
                manifest.model_dump_json(indent=2), encoding="utf-8"
            )
            evaluation = EvaluationRunner().evaluate(store.root)
            CalibrationSweepRunner().write_empty_sweep(store.root)
            RegressionGateRunner().check(store.root, None)
            SampleManifestBuilder().build(store.root)
            OverlaySampler().write_contact_sheet(store.root)
            metrics = (
                TrackingMetric(
                    name="raw_detection_count", value=float(evaluation.raw_detection_count)
                ),
                TrackingMetric(
                    name="cleaned_detection_count", value=float(evaluation.cleaned_detection_count)
                ),
                TrackingMetric(
                    name="rejected_detection_count",
                    value=float(evaluation.rejected_detection_count),
                ),
                TrackingMetric(name="interpolated_detection_count", value=0.0),
            )
            tracking_summary = TrackingRunSummary(
                run_suite_id=suite_id,
                run_id=run_id,
                experiment_id=ExperimentId(experiment.name),
                config_sha256=config_hash,
                dataset_file_count=self._dataset_file_count(config.runtime.data_root),
                clip_count=len(selected_clips),
                metrics=metrics,
                artifact_paths=(
                    store.root / "evaluation.json",
                    store.root / "regression.json",
                    store.root / "run-manifest.json",
                ),
                run_root=store.root,
            )
            mlflow_status = MlflowExperimentTracker(config.runtime.mlflow_tracking_uri).log_run(
                tracking_summary
            )
            dvc_status = DvcLiveTracker(config.runtime.dvclive_root).log_run(tracking_summary)
            evidently_status = EvidentlyReportWriter().write(tracking_summary)
            TrackingExportStatusWriter().write(
                TrackingExportStatus(
                    mlflow=mlflow_status, dvc=dvc_status, evidently=evidently_status
                ),
                store.root,
            )
            catalog.append_metrics(
                [
                    {
                        "run_suite_id": str(suite_id),
                        "run_id": str(run_id),
                        "experiment_id": experiment.name,
                        "config_sha256": config_hash,
                        "metric_name": metric.name,
                        "metric_value": metric.value,
                    }
                    for metric in metrics
                ]
            )
            self._append_run_index(
                catalog, run_id, suite_id, experiment.name, config_hash, len(selected_clips)
            )
            StaticReportBuilder().build(store.root)
            self._write_suite_summary(store.root, clip_summaries)
            run_ids.append(run_id)

        retention.prune_default_runtime(
            protect=(
                config.runtime.runs_root / str(suite_id),
                config.runtime.dvclive_root / str(suite_id),
                config.runtime.evidently_root / str(suite_id),
            )
        )
        return run_ids

    def _append_run_index(
        self,
        catalog: RunCatalog,
        run_id: RunId,
        suite_id: RunSuiteId,
        experiment_name: str,
        config_hash: str,
        clip_count: int,
    ) -> None:
        from handdetect.runs.manifest import RunIndexRow

        catalog.append_run(
            RunIndexRow(
                run_id=run_id,
                run_suite_id=suite_id,
                experiment_id=ExperimentId(experiment_name),
                code_version="0.1.0",
                config_sha256=config_hash,
                clip_count=clip_count,
            )
        )

    def _dataset_file_count(self, data_root: Path) -> int:
        return sum(1 for path in data_root.rglob("*") if path.is_file())

    def _write_suite_summary(self, run_root: Path, clip_summaries: list[object]) -> None:
        output = run_root / "suite-summary.json"
        output.write_text(
            json.dumps([summary.model_dump(mode="json") for summary in clip_summaries], indent=2),
            encoding="utf-8",
        )
