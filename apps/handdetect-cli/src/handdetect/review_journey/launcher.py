from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dq_contracts.ids import RunId, RunSuiteId
from handdetect.report.static_report import StaticReportBuilder
from handdetect.review.biodock_external_tables import (
    BiodockExternalTableArtifactPublisher,
    BiodockExternalTablePublication,
)
from handdetect.review.cvat_export import (
    CvatCorrectionImporter,
    CvatHandoffExporter,
    CvatPublisherConfig,
)
from handdetect.review.datumaro_export import DatumaroHandoffExporter
from handdetect.review.fiftyone_dataset import FiftyOneDatasetPublisher
from handdetect.review.labelstudio_client import LabelStudioPublisher
from handdetect.review.rerun_export import RerunExportConfig, RerunRecordingExporter
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
        workbench_url = self._workbench_url(runtime)
        StoryArtifactBuilder().build(run_root, workbench_url)
        biodock_publication, biodock_error = self._publish_biodock_external_tables(
            runtime,
            run_root,
        )
        dataset_name, fiftyone_url, fiftyone_error = FiftyOneDatasetPublisher().publish(
            suite_id, run_id, run_root
        )
        label_status = self._label_studio_status(runtime, run_root)
        cvat_config = CvatPublisherConfig(
            internal_url=runtime.cvat_url,
            public_url=runtime.cvat_public_url,
            username=runtime.cvat_username,
            password=runtime.cvat_password,
        )
        cvat_status = CvatHandoffExporter().export(run_root, cvat_config)
        cvat_corrections = CvatCorrectionImporter().import_corrections(run_root, cvat_config)
        datumaro_status = DatumaroHandoffExporter().export(
            run_root,
            (
                f"{workbench_url}/artifacts/{suite_id}/{run_id}"
                "/review/datumaro/diff-manifest.json"
            ),
            runtime.datumaro_url,
        )
        rerun_status = RerunRecordingExporter().export(
            run_root,
            RerunExportConfig(
                public_url=runtime.rerun_public_url,
                workbench_public_url=workbench_url,
            ),
        )
        manifest = ReviewPlatformManifest(
            run_suite_id=suite_id,
            run_id=run_id,
            report=ReviewPlatformStatus(
                status="ready",
                url=f"{self._workbench_url(runtime)}/artifacts/{suite_id}/{run_id}/report/index.html",
                path=run_root / "report" / "index.html",
                message="Static report hub",
            ),
            biodock=self._biodock_status(
                runtime,
                workbench_url,
                suite_id,
                run_id,
                biodock_publication,
                biodock_error,
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
                url=self._evidently_url(tracking["evidently"], runtime, suite_id, run_id),
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
            cvat=ReviewPlatformStatus(
                status=cvat_status.status,
                url=cvat_status.url,
                path=cvat_status.path,
                message=_cvat_message(cvat_status.message, cvat_corrections.message),
                imported_task_count=cvat_status.imported_task_count,
                task_id=cvat_status.task_id,
                job_ids=cvat_status.job_ids,
                job_urls=cvat_status.job_urls,
                correction_path=cvat_corrections.path,
                label_set_id=cvat_corrections.label_set_id,
                annotation_sha256=cvat_corrections.annotation_sha256,
                shape_count=cvat_corrections.shape_count,
            ),
            datumaro=ReviewPlatformStatus(
                status=datumaro_status.status,
                url=datumaro_status.url,
                path=datumaro_status.path,
                message=datumaro_status.message,
            ),
            rerun=ReviewPlatformStatus(
                status=rerun_status.status,
                url=rerun_status.url,
                path=rerun_status.path,
                message=rerun_status.message,
                recording_url=rerun_status.recording_url,
            ),
            fiftyone_dataset=dataset_name,
        )
        output = run_root / "review" / "platforms.json"
        output.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        StoryArtifactBuilder().build(run_root, workbench_url)
        StaticReportBuilder().build(run_root)
        return manifest

    def _workbench_url(self, runtime: RuntimeConfig) -> str:
        if runtime.workbench_public_url:
            return str(runtime.workbench_public_url).rstrip("/")
        return f"http://{runtime.workbench_host}:{runtime.workbench_port}"

    def _biodock_status(
        self,
        runtime: RuntimeConfig,
        workbench_url: str,
        suite_id: RunSuiteId,
        run_id: RunId,
        publication: BiodockExternalTablePublication | None,
        registration_error: str,
    ) -> ReviewPlatformStatus:
        if not runtime.biodock_public_url:
            return ReviewPlatformStatus(
                status="not_configured",
                url=None,
                path=Path("generator-package/generator-package-manifest.json"),
                message="Set HANDDETECT_BIODOCK_PUBLIC_URL to activate the package in Berg10",
            )
        story_url = f"{workbench_url}/runs/{suite_id}/{run_id}/story"
        params = {
            "generator_package_bundle_url": f"{workbench_url}/generator-package/bundle.json",
            "generator_package_id": "handdetect_quality_adapter",
            "generator_workspace_id": "handdetect_quality_story",
            "generator_workspace_layout_id": "handdetect_customer_demo_console",
            "generator_package_name": "HandDetect Quality Adapter",
            "generator_review_url": story_url,
            "generator_run_suite_id": str(suite_id),
            "generator_run_id": str(run_id),
        }
        if publication is not None:
            params.update(
                {
                    "generator_external_source_locator": publication.source.raw_locator,
                    "generator_external_source_registration_id": (
                        publication.source.registration_id
                    ),
                    "generator_external_source_object_fingerprint": (
                        publication.source.object_fingerprint
                    ),
                    "generator_external_source_file_count": str(publication.source.file_count),
                    "generator_external_source_byte_length": str(publication.source.byte_length),
                    "generator_external_table_id": publication.table.table_id,
                    "generator_external_table_display_name": publication.table.display_name,
                    "generator_external_table_relative_pattern": (
                        publication.table.relative_pattern
                    ),
                    "generator_external_table_schema_ref": publication.table.schema_ref,
                    "generator_external_table_schema_fingerprint": ",".join(
                        str(item) for item in publication.table.schema_fingerprint
                    ),
                    "generator_external_table_refresh_policy": "manual_refresh",
                }
            )
        query = urlencode(params)
        status = "ready" if not registration_error else "degraded"
        message = (
            "BioDock Berg10 external generator package activation URL"
            if not registration_error
            else f"BioDock source files are ready; SDK registration degraded: {registration_error}"
        )
        return ReviewPlatformStatus(
            status=status,
            url=f"{runtime.biodock_public_url.rstrip('/')}?{query}",
            path=publication.rows_path
            if publication is not None
            else Path("generator-package/generator-package-manifest.json"),
            message=message,
        )

    def _publish_biodock_external_tables(
        self,
        runtime: RuntimeConfig,
        run_root: Path,
    ) -> tuple[BiodockExternalTablePublication | None, str]:
        if runtime.biodock_external_table_root is None:
            return None, ""
        publisher = BiodockExternalTableArtifactPublisher()
        try:
            publication = publisher.write_story_rows(
                run_root,
                runtime.biodock_external_table_root,
            )
            if runtime.biodock_rpc_url:
                publisher.register_with_biodock(
                    publication,
                    access_token=_biodock_access_token(runtime),
                    rpc_url=runtime.biodock_rpc_url,
                )
            return publication, ""
        except Exception as exc:
            return None, str(exc)

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

    def _evidently_url(
        self,
        evidently_status: dict[str, object],
        runtime: RuntimeConfig,
        suite_id: RunSuiteId,
        run_id: RunId,
    ) -> str:
        project_id = str(evidently_status.get("project_id") or "").strip()
        snapshot_id = str(evidently_status.get("snapshot_id") or "").strip()
        if runtime.evidently_public_url and project_id:
            project_url = f"{runtime.evidently_public_url.rstrip('/')}/projects/{project_id}"
            if snapshot_id:
                return f"{project_url}/reports/{snapshot_id}"
            return project_url
        return f"{self._workbench_url(runtime)}/artifacts/{suite_id}/{run_id}/report/evidently.html"

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


def _biodock_access_token(runtime: RuntimeConfig) -> str | None:
    if runtime.biodock_access_token:
        return runtime.biodock_access_token
    if not (
        runtime.biodock_token_url
        and runtime.biodock_client_id
        and runtime.biodock_client_secret
    ):
        return None
    payload = urlencode(
        {
            "client_id": runtime.biodock_client_id,
            "client_secret": runtime.biodock_client_secret,
            "grant_type": "client_credentials",
        }
    ).encode("utf-8")
    request = Request(
        runtime.biodock_token_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            token_response = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("BioDock client-credentials token request failed") from exc
    token = token_response.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("BioDock token response did not include access_token")
    return token


def _cvat_message(handoff_message: str, correction_message: str) -> str:
    if not correction_message:
        return handoff_message
    return f"{handoff_message}; {correction_message}"
