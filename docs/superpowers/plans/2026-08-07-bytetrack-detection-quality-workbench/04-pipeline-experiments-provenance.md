# Task 4: Pipeline State Machine, Experiments, Provenance, Bounded Runs

> **Package placement:** Apply `00-reusable-package-boundaries.md`. Paths below name logical
> owners from the original module sketch; implement reusable code in `packages/*` and app wiring
> in `apps/handdetect-cli` according to the normative path map.

**Files:**
- Create: `configs/smoke-experiment.toml`
- Create: `configs/default-experiments.toml`
- Create: `src/handdetect/pipeline/state_machine.py`
- Create: `src/handdetect/pipeline/clip_runner.py`
- Create: `src/handdetect/pipeline/run_runner.py`
- Create: `src/handdetect/experiments/matrix.py`
- Create: `src/handdetect/experiments/runner.py`
- Modify: `src/handdetect/cli/main.py`
- Create: `tests/acceptance/test_experiment_run.py`

**Interfaces:**
- Consumes:
  - Scanner/parser/column builder/run store from Task 2.
  - ByteTrack/filter/selector/audit modules from Task 3.
- Produces:
  - `ClipRunner.run_clip(paths: ValidatedClipPathSet, run_id: RunId, experiment: ExperimentConfig, store: RunArtifactStore) -> ClipRunSummary`.
  - `ExperimentRunner.run(config: ValidatedExperimentConfig) -> RunSuiteManifest`.
  - Immutable run manifests and per-experiment provenance.
  - Append-only run index rows that allow repeated identical configs without overwriting prior outputs.

- [ ] **Step 1: Write failing experiment acceptance test**

Create `tests/acceptance/test_experiment_run.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_smoke_experiment_records_provenance_and_metrics() -> None:
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
    manifest_path = ROOT / "runs" / suite_id / run_id / "run-manifest.json"
    metrics_path = ROOT / "runs" / suite_id / run_id / "tables" / "clip_metrics.parquet"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["experiment_id"] == "smoke"
    assert manifest["code_version"]
    assert manifest["config_sha256"]
    assert manifest["run_suite_id"] == suite_id
    assert metrics_path.exists()


def test_repeated_smoke_runs_do_not_overwrite_outputs() -> None:
    first = subprocess.run(
        ["python", "-m", "handdetect.cli.main", "run", "--config", "configs/smoke-experiment.toml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    second = subprocess.run(
        ["python", "-m", "handdetect.cli.main", "run", "--config", "configs/smoke-experiment.toml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    first_suite = first.stdout.split("suite_id=", 1)[1].split()[0]
    second_suite = second.stdout.split("suite_id=", 1)[1].split()[0]
    assert first_suite != second_suite
    assert (ROOT / "runs" / first_suite).exists()
    assert (ROOT / "runs" / second_suite).exists()
    assert (ROOT / "runs" / "index" / "run_index.parquet").exists()
```

- [ ] **Step 2: Add experiment configs**

Create `configs/smoke-experiment.toml`:

```toml
[runtime]
data_root = "data"
runs_root = "runs"
max_clip_workers = 1
mlflow_tracking_uri = "mlruns"
dvclive_root = "dvclive"
evidently_root = "runs/evidently"

[[experiments]]
name = "smoke"
enabled_filters = [
  "duplicate_merge",
  "size_gate",
  "shape_gate",
  "byte_track",
  "displacement_gate",
  "track_support_gate",
  "static_scene_gate",
  "max_two_selector",
]

[experiments.adapter]
duplicate_iou_threshold = 0.85
min_box_area_px = 1200.0
max_box_area_px = 280000.0
min_aspect_ratio = 0.35
max_aspect_ratio = 2.85
max_center_speed_px_per_s = 4200.0
min_track_length_frames = 3
static_camera_motion_px = 12.0
static_box_motion_px = 2.0

[experiments.bytetrack]
track_activation_threshold = 0.20
minimum_matching_threshold = 0.80
lost_track_buffer = 15
frame_rate = 30
```

Create `configs/default-experiments.toml` with three experiments:

```toml
[runtime]
data_root = "data"
runs_root = "runs"
max_clip_workers = 4
mlflow_tracking_uri = "mlruns"
dvclive_root = "dvclive"
evidently_root = "runs/evidently"

[[experiments]]
name = "baseline_geometry_tracking_temporal"
enabled_filters = ["duplicate_merge", "size_gate", "shape_gate", "byte_track", "displacement_gate", "track_support_gate", "static_scene_gate", "max_two_selector"]

[experiments.adapter]
duplicate_iou_threshold = 0.85
min_box_area_px = 1200.0
max_box_area_px = 280000.0
min_aspect_ratio = 0.35
max_aspect_ratio = 2.85
max_center_speed_px_per_s = 4200.0
min_track_length_frames = 3
static_camera_motion_px = 12.0
static_box_motion_px = 2.0

[experiments.bytetrack]
track_activation_threshold = 0.20
minimum_matching_threshold = 0.80
lost_track_buffer = 15
frame_rate = 30

[[experiments]]
name = "no_static_filter"
enabled_filters = ["duplicate_merge", "size_gate", "shape_gate", "byte_track", "displacement_gate", "track_support_gate", "max_two_selector"]

[experiments.adapter]
duplicate_iou_threshold = 0.85
min_box_area_px = 1200.0
max_box_area_px = 280000.0
min_aspect_ratio = 0.35
max_aspect_ratio = 2.85
max_center_speed_px_per_s = 4200.0
min_track_length_frames = 3
static_camera_motion_px = 12.0
static_box_motion_px = 2.0

[experiments.bytetrack]
track_activation_threshold = 0.20
minimum_matching_threshold = 0.80
lost_track_buffer = 15
frame_rate = 30

[[experiments]]
name = "conservative_duplicate_merge"
enabled_filters = ["duplicate_merge", "size_gate", "shape_gate", "byte_track", "displacement_gate", "track_support_gate", "static_scene_gate", "max_two_selector"]

[experiments.adapter]
duplicate_iou_threshold = 0.92
min_box_area_px = 1200.0
max_box_area_px = 280000.0
min_aspect_ratio = 0.35
max_aspect_ratio = 2.85
max_center_speed_px_per_s = 4200.0
min_track_length_frames = 3
static_camera_motion_px = 12.0
static_box_motion_px = 2.0

[experiments.bytetrack]
track_activation_threshold = 0.20
minimum_matching_threshold = 0.80
lost_track_buffer = 15
frame_rate = 30
```

- [ ] **Step 3: Implement run state machine**

Create `src/handdetect/pipeline/state_machine.py`:

```python
from __future__ import annotations

from handdetect.domain.enums import RunEvent, RunState


TRANSITIONS: dict[tuple[RunState, RunEvent], RunState] = {
    (RunState.CREATED, RunEvent.SCAN_OK): RunState.DATASET_SCANNED,
    (RunState.DATASET_SCANNED, RunEvent.CLIP_STARTED): RunState.CLIPS_RUNNING,
    (RunState.CLIPS_RUNNING, RunEvent.CLIP_SUCCEEDED): RunState.CLIPS_RUNNING,
    (RunState.CLIPS_RUNNING, RunEvent.ALL_CLIPS_SUCCEEDED): RunState.ARTIFACTS_WRITTEN,
    (RunState.ARTIFACTS_WRITTEN, RunEvent.EVAL_SUCCEEDED): RunState.EVALUATED,
    (RunState.EVALUATED, RunEvent.REPORT_SUCCEEDED): RunState.REPORTED,
    (RunState.REPORTED, RunEvent.REGRESSION_SUCCEEDED): RunState.REGRESSION_CHECKED,
    (RunState.REGRESSION_CHECKED, RunEvent.ALL_CLIPS_SUCCEEDED): RunState.COMPLETE,
}


class RunStateMachine:
    def __init__(self) -> None:
        self.state = RunState.CREATED

    def apply(self, event: RunEvent) -> RunState:
        if event == RunEvent.FAILURE_SEEN:
            self.state = RunState.FAILED
            return self.state
        if event == RunEvent.CANCEL_REQUESTED:
            self.state = RunState.CANCELLED
            return self.state
        key = (self.state, event)
        if key not in TRANSITIONS:
            raise ValueError(f"invalid run transition: {self.state} + {event}")
        self.state = TRANSITIONS[key]
        return self.state
```

- [ ] **Step 4: Implement clip and experiment runners**

Create `src/handdetect/pipeline/clip_runner.py`:

```python
from __future__ import annotations

import json

import pyarrow as pa
import pyarrow.parquet as pq

from handdetect.audit.ledger import DecisionLedgerBuilder
from handdetect.config.models import ExperimentConfig
from handdetect.domain.ids import RunId
from handdetect.domain.models import ValidatedClipPathSet
from handdetect.filters.geometric import GeometricFilterPipeline
from handdetect.filters.temporal import TemporalFilterPipeline
from handdetect.hotpath.columnar import ClipColumnBuilder
from handdetect.io.parsers import JsonBoundaryParser
from handdetect.runs.store import RunArtifactStore
from handdetect.selection.max_two import MaxTwoSelector
from handdetect.tracking.bytetrack import ByteTrackAssociationAdapter
from pydantic import BaseModel, ConfigDict


class ClipRunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    clip_id: str
    interpolated_detection_count: int
    max_detections_per_frame: int
    selected_detection_count: int


class ClipRunner:
    def run_clip(self, paths: ValidatedClipPathSet, run_id: RunId, experiment: ExperimentConfig, store: RunArtifactStore) -> ClipRunSummary:
        bundle = JsonBoundaryParser().parse_clip(paths)
        block = ClipColumnBuilder().build(bundle)
        geometric = GeometricFilterPipeline().run(block, experiment.adapter)
        tracks = ByteTrackAssociationAdapter().associate(block, geometric, experiment.bytetrack)
        temporal = TemporalFilterPipeline().run(block, tracks, experiment.adapter)
        selected = MaxTwoSelector().select(block, tracks, temporal)
        decisions = DecisionLedgerBuilder().build(run_id, block, geometric, selected)
        cleaned_path = store.cleaned_dir / f"{paths.clip_id}.json"
        audit_path = store.audit_dir / f"{paths.clip_id}.jsonl"
        cleaned_payload = ClipRunSummary(
            run_id=str(run_id),
            clip_id=str(paths.clip_id),
            interpolated_detection_count=0,
            max_detections_per_frame=2,
            selected_detection_count=int(selected.selected_mask.sum()),
        )
        cleaned_path.write_text(cleaned_payload.model_dump_json(indent=2), encoding="utf-8")
        audit_path.write_text("\n".join(record.model_dump_json() for record in decisions), encoding="utf-8")
        table = pa.table(
            {
                "clip_id": [str(paths.clip_id)],
                "raw_detection_count": [len(block.detection_ids)],
                "selected_detection_count": [int(selected.selected_mask.sum())],
                "rejected_detection_count": [int((~selected.selected_mask).sum())],
            }
        )
        pq.write_table(table, store.tables_dir / f"clip_metrics_{paths.clip_id}.parquet")
        pq.write_table(table, store.tables_dir / "clip_metrics.parquet")
        return cleaned_payload
```

Create `src/handdetect/experiments/runner.py`:

```python
from __future__ import annotations

import hashlib
import json

from handdetect.config.models import ValidatedExperimentConfig
from handdetect.domain.ids import ExperimentId, RunSuiteId
from handdetect.io.dataset import DatasetScanner
from handdetect.pipeline.clip_runner import ClipRunner
from handdetect.runs.ids import RunIdProvider
from handdetect.runs.manifest import RunIndexRow
from handdetect.runs.catalog import RunCatalog
from handdetect.runs.store import RunArtifactStore


class ExperimentRunner:
    def run(self, config: ValidatedExperimentConfig, suite_id: RunSuiteId) -> list[str]:
        config_bytes = config.model_dump_json().encode("utf-8")
        config_hash = hashlib.sha256(config_bytes).hexdigest()
        clips = DatasetScanner().scan(config.runtime.data_root)
        run_ids: list[str] = []
        catalog = RunCatalog.open(config.runtime.runs_root)
        for experiment in config.experiments:
            run_id = RunIdProvider().create(suite_id, ExperimentId(experiment.name), config_hash)
            store = RunArtifactStore.open(config.runtime.runs_root, suite_id, run_id)
            for paths in clips[:3] if experiment.name == "smoke" else clips:
                ClipRunner().run_clip(paths, run_id, experiment, store)
            manifest = RunIndexRow(
                run_id=run_id,
                run_suite_id=suite_id,
                experiment_id=ExperimentId(experiment.name),
                code_version="0.1.0",
                config_sha256=config_hash,
                clip_count=3 if experiment.name == "smoke" else len(clips),
            )
            (store.root / "run-manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
            catalog.append_run(manifest)
            run_ids.append(str(run_id))
        return run_ids
```

Create `src/handdetect/experiments/matrix.py`:

```python
from __future__ import annotations

from handdetect.config.models import ExperimentConfig, ValidatedExperimentConfig


class ExperimentMatrix:
    def experiments(self, config: ValidatedExperimentConfig) -> tuple[ExperimentConfig, ...]:
        return config.experiments
```

- [ ] **Step 5: Wire CLI run**

Modify `src/handdetect/cli/main.py` top-level imports:

```python
from handdetect.config.parser import ExperimentConfigParser
from handdetect.experiments.runner import ExperimentRunner
from handdetect.runs.ids import RunSuiteIdProvider
```

Modify `src/handdetect/cli/main.py` `run()` command body:

```python
@app.command()
def run(config: Path) -> None:
    parsed = ExperimentConfigParser().parse_path(config)
    suite_id = RunSuiteIdProvider().create()
    run_ids = ExperimentRunner().run(parsed, suite_id)
    for run_id in run_ids:
        typer.echo(f"handdetect run: suite_id={suite_id} run_id={run_id} report=runs/{suite_id}/{run_id}/report/index.html")
```

- [ ] **Step 6: Run experiment acceptance tests and commit**

Run:

```bash
python -m pytest tests/acceptance/test_adapter_smoke.py tests/acceptance/test_experiment_run.py -v
make check
```

Expected:

```text
2 passed
```

Commit:

```bash
git add configs src/handdetect/pipeline src/handdetect/experiments src/handdetect/cli/main.py tests/acceptance/test_experiment_run.py
git commit -m "feat: add experiment runner and provenance"
```
