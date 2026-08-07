from __future__ import annotations

import html
from importlib import import_module

import pandas as pd

from experiment_tracking.export_status import PlatformStatus
from experiment_tracking.interfaces import TrackingRunSummary


class EvidentlyReportWriter:
    def write(self, summary: TrackingRunSummary) -> PlatformStatus:
        output = summary.run_root / "report" / "evidently.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            report = self._build_report()
            report.run(
                current_data=pd.DataFrame(
                    {
                        "metric": [metric.name for metric in summary.metrics],
                        "value": [metric.value for metric in summary.metrics],
                    }
                ),
                name=f"{summary.run_suite_id}/{summary.run_id}",
            ).save_html(str(output))
            if not output.exists() or output.stat().st_size == 0:
                raise RuntimeError(f"Evidently did not create report artifact at {output}")
            return PlatformStatus(status="exported", path=str(output))
        except Exception as exc:
            output.write_text(self._fallback_html(summary, str(exc)), encoding="utf-8")
            return PlatformStatus(status="degraded", path=str(output), error=str(exc))

    def _build_report(self) -> object:
        evidently = import_module("evidently")
        presets = import_module("evidently.presets")
        return evidently.Report([presets.DataSummaryPreset()])

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
