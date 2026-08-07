# Task 7: Open-Source Experiment Tracking, Queryable Regression History

**Files:**
- Create: `src/handdetect/tracking_platforms/interfaces.py`
- Create: `src/handdetect/tracking_platforms/mlflow_tracker.py`
- Create: `src/handdetect/tracking_platforms/dvc_tracker.py`
- Create: `src/handdetect/tracking_platforms/evidently_report.py`
- Create: `src/handdetect/tracking_platforms/export_status.py`
- Modify: `src/handdetect/runs/catalog.py`
- Modify: `src/handdetect/experiments/runner.py`
- Modify: `src/handdetect/report/static_report.py`
- Create: `tests/acceptance/test_open_source_tracking.py`

**Interfaces:**
- Consumes:
  - `RunManifest` and run artifact paths from Task 4.
  - `EvaluationSummary` and `RegressionSummary` from Task 5.
  - `RunCatalog` from Task 2.
- Produces:
  - `ExperimentTracker.log_run(summary: TrackingRunSummary) -> TrackingExportStatus`.
  - `runs/<run_suite_id>/<run_id>/tracking_export_status.json`.
  - `mlruns/` local MLflow experiment and run records.
  - `dvclive/<run_suite_id>/<run_id>/metrics.json` and plot-ready metric files.
  - `runs/<run_suite_id>/<run_id>/report/evidently.html`.
  - Append-only `runs/index/run_index.parquet` and `runs/index/metric_history.parquet`.

- [ ] **Step 1: Write failing open-source tracking acceptance test**

Create `tests/acceptance/test_open_source_tracking.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import polars as pl


ROOT = Path(__file__).resolve().parents[2]


def test_smoke_run_exports_to_mlflow_dvc_evidently_and_history() -> None:
    result = subprocess.run(
        ["python", "-m", "handdetect.cli.main", "run", "--config", "configs/smoke-experiment.toml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    suite_id = result.stdout.split("suite_id=", 1)[1].split()[0]
    run_id = result.stdout.split("run_id=", 1)[1].split()[0]
    run_root = ROOT / "runs" / suite_id / run_id
    status = json.loads((run_root / "tracking_export_status.json").read_text(encoding="utf-8"))
    assert status["mlflow"]["status"] == "exported"
    assert status["dvc"]["status"] == "exported"
    assert status["evidently"]["status"] == "exported"
    assert (ROOT / "mlruns").exists()
    assert (ROOT / "dvclive" / suite_id / run_id / "metrics.json").exists()
    assert (run_root / "report" / "evidently.html").exists()
    history = pl.read_parquet(ROOT / "runs" / "index" / "metric_history.parquet")
    matching = history.filter((pl.col("run_suite_id") == suite_id) & (pl.col("run_id") == run_id))
    assert matching.height > 0
```

- [ ] **Step 2: Define tracking interfaces and export status**

Create `src/handdetect/tracking_platforms/interfaces.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from handdetect.domain.ids import ExperimentId, RunId, RunSuiteId


class TrackingMetric(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: float


class MetricHistoryRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_suite_id: str
    run_id: str
    experiment_id: str
    config_sha256: str
    metric_name: str
    metric_value: float


class TrackingRunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_suite_id: RunSuiteId
    run_id: RunId
    experiment_id: ExperimentId
    config_sha256: str
    dataset_file_count: int
    clip_count: int
    metrics: tuple[TrackingMetric, ...]
    artifact_paths: tuple[Path, ...]
    run_root: Path
```

Create `src/handdetect/tracking_platforms/export_status.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class PlatformStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    path: str
    error: str | None


class TrackingExportStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    mlflow: PlatformStatus
    dvc: PlatformStatus
    evidently: PlatformStatus


class TrackingExportStatusWriter:
    def write(self, status: TrackingExportStatus, run_root: Path) -> Path:
        output = run_root / "tracking_export_status.json"
        output.write_text(json.dumps(status.model_dump(), indent=2), encoding="utf-8")
        return output
```

- [ ] **Step 3: Implement MLflow tracker adapter**

Create `src/handdetect/tracking_platforms/mlflow_tracker.py`:

```python
from __future__ import annotations

from pathlib import Path

import mlflow

from handdetect.tracking_platforms.export_status import PlatformStatus
from handdetect.tracking_platforms.interfaces import TrackingRunSummary


class MlflowExperimentTracker:
    def __init__(self, tracking_uri: str) -> None:
        self.tracking_uri = tracking_uri

    def log_run(self, summary: TrackingRunSummary) -> PlatformStatus:
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(str(summary.experiment_id))
        with mlflow.start_run(run_name=str(summary.run_id)):
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
        return PlatformStatus(status="exported", path=str(Path(self.tracking_uri)), error=None)
```

- [ ] **Step 4: Implement DVC/DVCLive tracker adapter**

Create `src/handdetect/tracking_platforms/dvc_tracker.py`:

```python
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
        return PlatformStatus(status="exported", path=str(output), error=None)
```

- [ ] **Step 5: Implement Evidently report adapter**

Create `src/handdetect/tracking_platforms/evidently_report.py`:

```python
from __future__ import annotations

from pathlib import Path

from evidently import Report
from evidently.presets import DataSummaryPreset
import pandas as pd

from handdetect.tracking_platforms.export_status import PlatformStatus
from handdetect.tracking_platforms.interfaces import TrackingRunSummary


class EvidentlyReportWriter:
    def write(self, summary: TrackingRunSummary) -> PlatformStatus:
        rows = [{"metric": metric.name, "value": metric.value} for metric in summary.metrics]
        report = Report([DataSummaryPreset()])
        report.run(pd.DataFrame(rows), None)
        output = summary.run_root / "report" / "evidently.html"
        report.save_html(output)
        return PlatformStatus(status="exported", path=str(output), error=None)
```

- [ ] **Step 6: Extend run catalog with metric history**

Modify `src/handdetect/runs/catalog.py`:

```python
class RunCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.index_dir = root / "index"
        self.run_index_path = self.index_dir / "run_index.parquet"
        self.metric_history_path = self.index_dir / "metric_history.parquet"

    def append_metrics(self, rows: list[MetricHistoryRow]) -> None:
        with self._locked():
            values = [row.model_dump(mode="json") for row in rows]
            table = pa.table({key: [row[key] for row in values] for key in values[0]})
            if self.metric_history_path.exists():
                existing = pq.read_table(self.metric_history_path)
                table = pa.concat_tables([existing, table], promote_options="default")
            temp_path = self.metric_history_path.with_suffix(".tmp")
            pq.write_table(table, temp_path)
            temp_path.replace(self.metric_history_path)
```

- [ ] **Step 7: Wire tracking exports into experiment runner**

Modify `src/handdetect/experiments/runner.py` imports:

```python
from handdetect.tracking_platforms.dvc_tracker import DvcLiveTracker
from handdetect.tracking_platforms.evidently_report import EvidentlyReportWriter
from handdetect.tracking_platforms.export_status import TrackingExportStatus, TrackingExportStatusWriter
from handdetect.tracking_platforms.interfaces import MetricHistoryRow, TrackingMetric, TrackingRunSummary
from handdetect.tracking_platforms.mlflow_tracker import MlflowExperimentTracker
```

Add this after evaluation and regression are computed:

```python
metrics = (
    TrackingMetric(name="raw_detection_count", value=float(evaluation.raw_detection_count)),
    TrackingMetric(name="cleaned_detection_count", value=float(evaluation.cleaned_detection_count)),
    TrackingMetric(name="interpolated_detection_count", value=float(evaluation.interpolated_detection_count)),
)
tracking_summary = TrackingRunSummary(
    run_suite_id=suite_id,
    run_id=run_id,
    experiment_id=ExperimentId(experiment.name),
    config_sha256=config_hash,
    dataset_file_count=sum(1 for path in config.runtime.data_root.rglob("*") if path.is_file()),
    clip_count=manifest["clip_count"],
    metrics=metrics,
    artifact_paths=(store.root / "regression.json", store.root / "run-manifest.json"),
    run_root=store.root,
)
mlflow_status = MlflowExperimentTracker(config.runtime.mlflow_tracking_uri).log_run(tracking_summary)
dvc_status = DvcLiveTracker(config.runtime.dvclive_root).log_run(tracking_summary)
evidently_status = EvidentlyReportWriter().write(tracking_summary)
TrackingExportStatusWriter().write(
    TrackingExportStatus(mlflow=mlflow_status, dvc=dvc_status, evidently=evidently_status),
    store.root,
)
catalog.append_metrics(
    [
        MetricHistoryRow(
            run_suite_id=str(suite_id),
            run_id=str(run_id),
            experiment_id=experiment.name,
            config_sha256=config_hash,
            metric_name=metric.name,
            metric_value=metric.value,
        )
        for metric in metrics
    ]
)
```

- [ ] **Step 8: Update static report with platform links**

Modify `src/handdetect/report/static_report.py` so `build()` reads `tracking_export_status.json` and renders:

```python
tracking = json.loads((run_root / "tracking_export_status.json").read_text(encoding="utf-8"))
```

Add inside the HTML body:

```html
  <section>
    <h2>Open-Source Tracking</h2>
    <p>MLflow: <code>{tracking["mlflow"]["path"]}</code></p>
    <p>DVC: <code>{tracking["dvc"]["path"]}</code></p>
    <p>Evidently: <code>{tracking["evidently"]["path"]}</code></p>
  </section>
```

- [ ] **Step 9: Run tracking acceptance test and commit**

Run:

```bash
python -m pytest tests/acceptance/test_open_source_tracking.py -v
make verify
```

Expected:

```text
1 passed
```

Commit:

```bash
git add src/handdetect/tracking_platforms src/handdetect/runs/catalog.py src/handdetect/experiments/runner.py src/handdetect/report/static_report.py tests/acceptance/test_open_source_tracking.py
git commit -m "feat: add open-source experiment tracking"
```
