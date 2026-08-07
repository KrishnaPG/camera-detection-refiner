from __future__ import annotations

from handdetect.tracking_platforms.export_status import PlatformStatus
from handdetect.tracking_platforms.interfaces import TrackingRunSummary


class EvidentlyReportWriter:
    def write(self, summary: TrackingRunSummary) -> PlatformStatus:
        output = summary.run_root / "report" / "evidently.html"
        rows = "\n".join(
            f"<tr><td>{metric.name}</td><td>{metric.value:.2f}</td></tr>"
            for metric in summary.metrics
        )
        html = (
            "<!doctype html><html><body><h1>Evidently Summary</h1>"
            "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></body></html>\n"
        )
        output.write_text(html, encoding="utf-8")
        return PlatformStatus(status="exported", path=str(output))
