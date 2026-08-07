# Task 1: Repository DX, Dependencies, Domain Contracts

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `.env.example`
- Create: `src/handdetect/__init__.py`
- Create: `src/handdetect/domain/ids.py`
- Create: `src/handdetect/domain/enums.py`
- Create: `src/handdetect/domain/constants.py`
- Create: `src/handdetect/domain/models.py`
- Create: `src/handdetect/config/models.py`
- Create: `src/handdetect/config/parser.py`
- Create: `src/handdetect/observability/names.py`
- Create: `src/handdetect/cli/main.py`
- Create: `tests/acceptance/test_cli_contract.py`

**Interfaces:**
- Produces:
  - `ClipId`, `RunId`, `ExperimentId`, `DetectionId`, `TrackId`, `FrameIndex`, `TimestampNs` in `handdetect.domain.ids`.
  - `DetectionDecision`, `RejectReason`, `PipelinePhase`, `RunState`, `RunEvent`, `FilterName` in `handdetect.domain.enums`.
  - `AdapterConfig`, `RuntimeConfig`, `ExperimentConfig`, `ValidatedExperimentConfig` in `handdetect.config.models`.
  - `ExperimentConfigParser.parse_path(path: Path) -> ValidatedExperimentConfig`.
  - CLI command group `handdetect` with `doctor`, `seed`, `run`, `check`, `test`, `verify`, `migrate`, `clean`.
- Consumes:
  - Existing assignment data under `data/`.
  - Standards under `docs/coding-*.md`.

- [ ] **Step 1: Write failing CLI contract acceptance test**

Create `tests/acceptance/test_cli_contract.py`:

```python
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_make(target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", target],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_root_task_interface_exposes_required_targets() -> None:
    result = run_make("doctor")
    assert result.returncode == 0, result.stderr
    assert "handdetect doctor" in result.stdout


def test_cli_help_lists_public_commands() -> None:
    result = subprocess.run(
        ["python", "-m", "handdetect.cli.main", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    for command in ["doctor", "seed", "run", "check", "test", "verify", "migrate", "clean"]:
        assert command in result.stdout
```

- [ ] **Step 2: Run the failing acceptance test**

Run:

```bash
python -m pytest tests/acceptance/test_cli_contract.py -v
```

Expected:

```text
FAILED tests/acceptance/test_cli_contract.py::test_root_task_interface_exposes_required_targets
```

- [ ] **Step 3: Create pinned project metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling==1.28.0"]
build-backend = "hatchling.build"

[project]
name = "handdetect-quality"
version = "0.1.0"
description = "ByteTrack-backed hand detection quality workbench"
requires-python = "==3.12.*"
dependencies = [
  "fiftyone==1.20.1",
  "numpy==2.5.1",
  "opencv-python-headless==5.0.0.93",
  "opentelemetry-sdk==1.44.0",
  "polars==1.43.2",
  "prometheus-client==0.26.0",
  "pyarrow==25.0.0",
  "pydantic==2.13.4",
  "structlog==26.1.0",
  "supervision==0.30.0",
  "trackers==2.6.0",
  "typer==0.27.1",
]

[project.optional-dependencies]
dev = [
  "mypy==2.3.0",
  "pytest==9.0.2",
  "pytest-xdist==3.8.0",
  "ruff==0.16.1",
]

[project.scripts]
handdetect = "handdetect.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/handdetect"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_unused_configs = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_decorators = true
no_implicit_optional = true
```

- [ ] **Step 4: Create root task interface**

Create `Makefile`:

```make
.PHONY: bootstrap doctor run check test verify seed migrate clean

PYTHON ?= python

bootstrap:
	$(PYTHON) -m pip install --upgrade pip==26.2.1
	$(PYTHON) -m pip install -e ".[dev]"

doctor:
	$(PYTHON) -m handdetect.cli.main doctor

run:
	$(PYTHON) -m handdetect.cli.main run --config configs/default-experiments.toml

check:
	$(PYTHON) -m ruff format --check src tests
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m mypy src

test:
	$(PYTHON) -m pytest tests/acceptance -v

verify: check test

seed:
	$(PYTHON) -m handdetect.cli.main seed --data-root data --out runs/seed/seed-manifest.json

migrate:
	$(PYTHON) -m handdetect.cli.main migrate

clean:
	$(PYTHON) -m handdetect.cli.main clean --runs-root runs
```

Create `.env.example`:

```dotenv
HANDDETECT_DATA_ROOT=data
HANDDETECT_RUNS_ROOT=runs
HANDDETECT_MAX_CLIP_WORKERS=4
HANDDETECT_OTEL_EXPORTER=none
```

- [ ] **Step 5: Create domain ids, enums, and constants**

Create `src/handdetect/domain/ids.py`:

```python
from __future__ import annotations

from typing import NewType

ClipId = NewType("ClipId", str)
RunId = NewType("RunId", str)
ExperimentId = NewType("ExperimentId", str)
DetectionId = NewType("DetectionId", str)
TrackId = NewType("TrackId", int)
FrameIndex = NewType("FrameIndex", int)
TimestampNs = NewType("TimestampNs", int)
```

Create `src/handdetect/domain/enums.py`:

```python
from __future__ import annotations

from enum import StrEnum


class DetectionDecision(StrEnum):
    KEPT = "kept"
    MERGED = "merged"
    REJECTED = "rejected"


class RejectReason(StrEnum):
    DUPLICATE_OVERLAP = "duplicate_overlap"
    IMPLAUSIBLE_SIZE = "implausible_size"
    IMPLAUSIBLE_SHAPE = "implausible_shape"
    IMPLAUSIBLE_DISPLACEMENT = "implausible_displacement"
    UNSUPPORTED_TRACK = "unsupported_track"
    STATIC_SCENE = "static_scene"
    OVER_MAX_HANDS = "over_max_hands"


class FilterName(StrEnum):
    DUPLICATE_MERGE = "duplicate_merge"
    SIZE_GATE = "size_gate"
    SHAPE_GATE = "shape_gate"
    BYTE_TRACK = "byte_track"
    DISPLACEMENT_GATE = "displacement_gate"
    TRACK_SUPPORT_GATE = "track_support_gate"
    STATIC_SCENE_GATE = "static_scene_gate"
    MAX_TWO_SELECTOR = "max_two_selector"


class PipelinePhase(StrEnum):
    LOAD = "load"
    COLUMNAR = "columnar"
    GEOMETRIC = "geometric"
    TRACKING = "tracking"
    TEMPORAL = "temporal"
    SELECTION = "selection"
    ARTIFACTS = "artifacts"
    EVALUATION = "evaluation"
    REPORT = "report"
    REGRESSION = "regression"


class RunState(StrEnum):
    CREATED = "created"
    DATASET_SCANNED = "dataset_scanned"
    CLIPS_RUNNING = "clips_running"
    ARTIFACTS_WRITTEN = "artifacts_written"
    EVALUATED = "evaluated"
    REPORTED = "reported"
    REGRESSION_CHECKED = "regression_checked"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunEvent(StrEnum):
    SCAN_OK = "scan_ok"
    CLIP_STARTED = "clip_started"
    CLIP_SUCCEEDED = "clip_succeeded"
    CLIP_FAILED = "clip_failed"
    ALL_CLIPS_SUCCEEDED = "all_clips_succeeded"
    EVAL_SUCCEEDED = "eval_succeeded"
    REPORT_SUCCEEDED = "report_succeeded"
    REGRESSION_SUCCEEDED = "regression_succeeded"
    FAILURE_SEEN = "failure_seen"
    CANCEL_REQUESTED = "cancel_requested"
```

Create `src/handdetect/domain/constants.py`:

```python
from __future__ import annotations

FRAME_WIDTH_PX = 1920
FRAME_HEIGHT_PX = 1200
DATASET_FPS = 30.0
MAX_HANDS_PER_FRAME = 2
BYTE_TRACK_CLASS_ID = 0
AUDIT_JSONL_SUFFIX = ".jsonl"
CLEANED_JSON_SUFFIX = ".json"
PARQUET_SUFFIX = ".parquet"
```

- [ ] **Step 6: Create Pydantic domain and config models**

Create `src/handdetect/domain/models.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from handdetect.domain.enums import DetectionDecision, FilterName, RejectReason
from handdetect.domain.ids import ClipId, DetectionId, FrameIndex, RunId, TimestampNs, TrackId


class BoxXYXY(BaseModel):
    model_config = ConfigDict(frozen=True)

    x1: float
    y1: float
    x2: float
    y2: float


class RawDetection(BaseModel):
    model_config = ConfigDict(frozen=True)

    frame: FrameIndex
    xyxy: BoxXYXY
    confidence: float = Field(ge=0.0, le=1.0)
    class_id: int
    handedness: str


class ValidatedClipPathSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    clip_id: ClipId
    clip_dir: Path
    meta_path: Path
    hand_boxes_path: Path
    frame_ts_path: Path
    vio_pose_path: Path
    video_left_path: Path
    video_right_path: Path


class DetectionDecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: RunId
    clip_id: ClipId
    detection_id: DetectionId
    frame: FrameIndex
    decision: DetectionDecision
    stage: FilterName
    reason: RejectReason | None
    track_id: TrackId | None
    merged_into: DetectionId | None
    timestamp_ns: TimestampNs
```

Create `src/handdetect/config/models.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class AdapterConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    duplicate_iou_threshold: float = Field(gt=0.0, lt=1.0)
    min_box_area_px: float = Field(gt=0.0)
    max_box_area_px: float = Field(gt=0.0)
    min_aspect_ratio: float = Field(gt=0.0)
    max_aspect_ratio: float = Field(gt=0.0)
    max_center_speed_px_per_s: float = Field(gt=0.0)
    min_track_length_frames: int = Field(ge=1)
    static_camera_motion_px: float = Field(ge=0.0)
    static_box_motion_px: float = Field(ge=0.0)


class ByteTrackConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    track_activation_threshold: float = Field(gt=0.0, lt=1.0)
    minimum_matching_threshold: float = Field(gt=0.0, lt=1.0)
    lost_track_buffer: int = Field(ge=1)
    frame_rate: int = Field(ge=1)


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_root: Path
    runs_root: Path
    max_clip_workers: int = Field(ge=1)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    adapter: AdapterConfig
    bytetrack: ByteTrackConfig
    enabled_filters: tuple[str, ...]


class ValidatedExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime: RuntimeConfig
    experiments: tuple[ExperimentConfig, ...]
```

Create `src/handdetect/config/parser.py`:

```python
from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import ValidationError

from handdetect.config.models import ValidatedExperimentConfig


class ConfigParseError(RuntimeError):
    def __init__(self, path: Path, cause: ValidationError | OSError) -> None:
        super().__init__(f"failed to parse experiment config at {path}: {cause}")
        self.path = path
        self.cause = cause


class ExperimentConfigParser:
    def parse_path(self, path: Path) -> ValidatedExperimentConfig:
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
            return ValidatedExperimentConfig.model_validate(payload)
        except (ValidationError, OSError) as exc:
            raise ConfigParseError(path, exc) from exc
```

- [ ] **Step 7: Create CLI shell with public commands**

Create `src/handdetect/observability/names.py`:

```python
from __future__ import annotations

LOG_JOB_ID = "job_id"
LOG_STEP_ID = "step_id"
LOG_PHASE = "phase"
METRIC_RUNS_STARTED = "handdetect_runs_started_total"
METRIC_RUNS_FAILED = "handdetect_runs_failed_total"
METRIC_CLIP_SECONDS = "handdetect_clip_processing_seconds"
```

Create `src/handdetect/__init__.py`:

```python
from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create `src/handdetect/cli/main.py`:

```python
from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)


@app.command()
def doctor() -> None:
    typer.echo("handdetect doctor: ok")


@app.command()
def seed(data_root: Path, out: Path) -> None:
    typer.echo(f"handdetect seed: data_root={data_root} out={out}")


@app.command()
def run(config: Path) -> None:
    typer.echo(f"handdetect run: config={config}")


@app.command()
def check() -> None:
    typer.echo("handdetect check: use make check")


@app.command()
def test() -> None:
    typer.echo("handdetect test: use make test")


@app.command()
def verify() -> None:
    typer.echo("handdetect verify: use make verify")


@app.command()
def migrate() -> None:
    typer.echo("handdetect migrate: no migrations required")


@app.command()
def clean(runs_root: Path) -> None:
    typer.echo(f"handdetect clean: runs_root={runs_root}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 8: Run contract test and commit**

Run:

```bash
python -m pytest tests/acceptance/test_cli_contract.py -v
make check
```

Expected:

```text
2 passed
```

Commit:

```bash
git add pyproject.toml Makefile .env.example src/handdetect tests/acceptance/test_cli_contract.py
git commit -m "chore: add handdetect repo contract"
```

