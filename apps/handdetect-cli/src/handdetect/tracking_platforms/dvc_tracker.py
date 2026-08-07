from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from dvclive import Live
from handdetect.runtime_paths import runtime_state_root
from handdetect.tracking_platforms.export_status import PlatformStatus
from handdetect.tracking_platforms.interfaces import TrackingRunSummary


class DvcLiveTracker:
    def __init__(self, root: Path) -> None:
        self.root = root

    def log_run(self, summary: TrackingRunSummary) -> PlatformStatus:
        output = self.root / str(summary.run_suite_id) / str(summary.run_id)
        output.mkdir(parents=True, exist_ok=True)
        with (
            self._scoped_dvc_environment(),
            Live(
                dir=output,
                dvcyaml=False,
                save_dvc_exp=False,
            ) as live,
        ):
            for metric in summary.metrics:
                live.log_metric(metric.name, metric.value)
        return PlatformStatus(status="exported", path=str(output))

    @contextmanager
    def _scoped_dvc_environment(self) -> Iterator[None]:
        runtime_root = runtime_state_root()
        overrides = {
            "DVC_SITE_CACHE_DIR": str(runtime_root / "cache" / "dvc-site"),
            "XDG_CACHE_HOME": str(runtime_root / "cache"),
        }
        previous = {key: os.environ.get(key) for key in overrides}
        for path in overrides.values():
            Path(path).mkdir(parents=True, exist_ok=True)
        os.environ.update(overrides)
        try:
            yield
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
