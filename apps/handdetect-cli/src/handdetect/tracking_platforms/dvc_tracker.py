from __future__ import annotations

from pathlib import Path

from dvclive import Live
from handdetect.tracking_platforms.export_status import PlatformStatus
from handdetect.tracking_platforms.interfaces import TrackingRunSummary


class DvcLiveTracker:
    def __init__(self, root: Path) -> None:
        self.root = root

    def log_run(self, summary: TrackingRunSummary) -> PlatformStatus:
        output = self.root / str(summary.run_suite_id) / str(summary.run_id)
        with Live(dir=output, dvcyaml=False, save_dvc_exp=False) as live:
            for metric in summary.metrics:
                live.log_metric(metric.name, metric.value)
        return PlatformStatus(status="exported", path=str(output))
