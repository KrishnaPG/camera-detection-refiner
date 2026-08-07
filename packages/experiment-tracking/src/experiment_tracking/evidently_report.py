from __future__ import annotations

import html
from importlib import import_module
from pathlib import Path

import pandas as pd

from experiment_tracking.export_status import PlatformStatus
from experiment_tracking.interfaces import TrackingRunSummary


class EvidentlyReportWriter:
    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root

    def write(self, summary: TrackingRunSummary) -> PlatformStatus:
        output = summary.run_root / "report" / "evidently.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            report = self._build_report()
            snapshot = report.run(
                current_data=pd.DataFrame(
                    {
                        "metric": [metric.name for metric in summary.metrics],
                        "value": [metric.value for metric in summary.metrics],
                    }
                ),
                name=f"{summary.run_suite_id}/{summary.run_id}",
            )
            snapshot.save_html(str(output))
            if not output.exists() or output.stat().st_size == 0:
                raise RuntimeError(f"Evidently did not create report artifact at {output}")
            workspace = self._write_workspace(summary, snapshot)
            message = workspace.get("message") or "Evidently report exported"
            return PlatformStatus(
                status="exported",
                path=str(output),
                message=message,
                workspace_path=workspace.get("workspace_path"),
                project_id=workspace.get("project_id"),
                snapshot_id=workspace.get("snapshot_id"),
            )
        except Exception as exc:
            output.write_text(self._fallback_html(summary, str(exc)), encoding="utf-8")
            return PlatformStatus(status="degraded", path=str(output), error=str(exc))

    def _build_report(self) -> object:
        evidently = import_module("evidently")
        presets = import_module("evidently.presets")
        return evidently.Report([presets.DataSummaryPreset()])

    def _write_workspace(self, summary: TrackingRunSummary, snapshot: object) -> dict[str, str]:
        try:
            workspace_root = self._workspace_root or summary.run_root.parents[2] / "evidently"
            workspace_root.mkdir(parents=True, exist_ok=True)
            workspace_module = import_module("evidently.ui.workspace")
            workspace = workspace_module.Workspace(str(workspace_root))
            project = self._project(workspace)
            ref = workspace.add_run(
                project.id,
                snapshot,
                include_data=False,
                name=f"{summary.run_suite_id}/{summary.run_id}",
            )
            return {
                "workspace_path": str(workspace_root),
                "project_id": str(project.id),
                "snapshot_id": str(ref.id),
            }
        except Exception as exc:
            return {"message": f"Evidently HTML exported; workspace unavailable: {exc}"}

    def _project(self, workspace: object) -> object:
        for project in workspace.list_projects():
            if project.name == "HandDetect Regression":
                return project
        return workspace.create_project(
            name="HandDetect Regression",
            description="Run-scoped adapter quality reports",
        )

    def _fallback_html(self, summary: TrackingRunSummary, error: str) -> str:
        rows = "\n".join(
            (f"<tr><td>{html.escape(metric.name)}</td><td>{metric.value:.2f}</td></tr>")
            for metric in summary.metrics
        )
        return (
            "<!doctype html><html><body><h1>Evidently unavailable</h1>"
            f"<p>{html.escape(error)}</p>"
            "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></body></html>\n"
        )
