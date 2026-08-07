from __future__ import annotations

import json
from pathlib import Path

from dq_contracts.ids import RunId, RunSuiteId
from handdetect.report.static_report import StaticReportBuilder
from handdetect.review.fiftyone_dataset import FiftyOneDatasetPublisher
from handdetect.review.labelstudio_client import LabelStudioPublisher
from handdetect.review.story_artifacts import StoryArtifactBuilder
from handdetect.review_journey.models import ReviewPlatformManifest, ReviewPlatformStatus
from handdetect_domain.config import RuntimeConfig

MLFLOW_META_EXPERIMENT_PREFIX = "experiment_id:"
MLFLOW_RUN_ROUTE = "#/experiments/{experiment_id}/runs/{run_id}"


class ReviewJourneyLauncher:
    def open(
        self,
        suite_id: RunSuiteId,
        run_id: RunId,
        runtime: RuntimeConfig,
        run_root: Path,
    ) -> ReviewPlatformManifest:
        tracking = json.loads(
            (run_root / "tracking_export_status.json").read_text(encoding="utf-8")
        )
        dataset_name, fiftyone_url, fiftyone_error = FiftyOneDatasetPublisher().publish(
            suite_id, run_id, run_root
        )
        label_status = self._label_studio_status(runtime, run_root)
        manifest = ReviewPlatformManifest(
            run_suite_id=suite_id,
            run_id=run_id,
            report=ReviewPlatformStatus(
                status="ready",
                url=f"{self._workbench_url(runtime)}/artifacts/{suite_id}/{run_id}/report/index.html",
                path=run_root / "report" / "index.html",
                message="Static report hub",
            ),
            mlflow=ReviewPlatformStatus(
                status="ready",
                url=self._mlflow_url(tracking["mlflow"], runtime),
                path=Path(tracking["mlflow"]["path"]),
                message="MLflow run tracking",
            ),
            dvc=ReviewPlatformStatus(
                status="ready",
                url=None,
                path=Path(tracking["dvc"]["path"]),
                message=tracking["dvc"].get("message") or "DVCLive metrics directory",
            ),
            evidently=ReviewPlatformStatus(
                status="ready" if tracking["evidently"].get("status") == "exported" else "degraded",
                url=f"{self._workbench_url(runtime)}/artifacts/{suite_id}/{run_id}/report/evidently.html",
                path=Path(tracking["evidently"]["path"]),
                message=tracking["evidently"].get("error") or "Evidently report",
            ),
            fiftyone=ReviewPlatformStatus(
                status="ready" if fiftyone_url else "path_only",
                url=fiftyone_url,
                path=run_root / "review" / "fiftyone-dataset.json",
                message="FiftyOne dataset published"
                if fiftyone_url
                else f"FiftyOne dataset manifest only: {fiftyone_error}",
            ),
            label_studio=label_status,
            fiftyone_dataset=dataset_name,
        )
        output = run_root / "review" / "platforms.json"
        output.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        StoryArtifactBuilder().build(run_root, self._workbench_url(runtime))
        StaticReportBuilder().build(run_root)
        return manifest

    def _workbench_url(self, runtime: RuntimeConfig) -> str:
        if runtime.workbench_public_url:
            return runtime.workbench_public_url.rstrip("/")
        return f"http://{runtime.workbench_host}:{runtime.workbench_port}"

    def _mlflow_url(self, mlflow_status: dict[str, object], runtime: RuntimeConfig) -> str | None:
        base_url = str(mlflow_status.get("url") or runtime.mlflow_public_url or "").strip()
        run_id = str(mlflow_status.get("run_id") or "").strip()
        if not base_url or not run_id:
            return base_url or None
        experiment_id = _mlflow_experiment_id(Path(str(mlflow_status["path"])), run_id)
        if not experiment_id:
            return base_url.rstrip("/")
        return (
            f"{base_url.rstrip('/')}/"
            f"{MLFLOW_RUN_ROUTE.format(experiment_id=experiment_id, run_id=run_id)}"
        )

    def _label_studio_status(self, runtime: RuntimeConfig, run_root: Path) -> ReviewPlatformStatus:
        tasks_path = run_root / "review" / "labelstudio-tasks.json"
        if runtime.label_studio_url and runtime.label_studio_token:
            try:
                project_id, imported = LabelStudioPublisher().publish(
                    run_root,
                    runtime.label_studio_url,
                    runtime.label_studio_token,
                )
                public_url = runtime.label_studio_public_url or runtime.label_studio_url
                return ReviewPlatformStatus(
                    status="ready",
                    url=f"{public_url.rstrip('/')}/projects/{project_id}",
                    path=tasks_path,
                    message="Label Studio project created",
                    project_id=project_id,
                    imported_task_count=imported,
                )
            except Exception as exc:
                return ReviewPlatformStatus(
                    status="import_file",
                    url=None,
                    path=tasks_path,
                    message=f"Label Studio export fallback: {exc}",
                )
        return ReviewPlatformStatus(
            status="import_file",
            url=None,
            path=tasks_path,
            message="Import this task file into Label Studio",
        )


def _mlflow_experiment_id(tracking_root: Path, run_id: str) -> str | None:
    for meta_path in tracking_root.glob(f"*/{run_id}/meta.yaml"):
        experiment_id = _read_mlflow_experiment_id(meta_path)
        if experiment_id:
            return experiment_id
    return None


def _read_mlflow_experiment_id(meta_path: Path) -> str | None:
    for line in meta_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(MLFLOW_META_EXPERIMENT_PREFIX):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None
