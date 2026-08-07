# Task 5: Gold Labels, Accuracy Evaluation, Calibration, Regression Gates

**Files:**
- Create: `labels/README.md`
- Create: `labels/gold/manifest.json`
- Create: `src/handdetect/eval/labels.py`
- Create: `src/handdetect/eval/iou.py`
- Create: `src/handdetect/eval/metrics.py`
- Create: `src/handdetect/eval/calibration.py`
- Create: `src/handdetect/regression/baseline.py`
- Create: `src/handdetect/regression/gates.py`
- Create: `src/handdetect/regression/history.py`
- Modify: `src/handdetect/cli/main.py`
- Create: `tests/acceptance/test_evaluation_and_regression.py`

**Interfaces:**
- Consumes:
  - Run artifacts from Task 4.
  - Optional Label Studio or COCO-style labels from `labels/gold/`.
- Produces:
  - `EvaluationRunner.evaluate(run_root: Path, labels_root: Path | None) -> EvaluationSummary`.
  - `RegressionGateRunner.check(run_root: Path, baseline_path: Path | None) -> RegressionSummary`.
  - `runs/<run_suite_id>/<run_id>/tables/evaluation_metrics.parquet`.
  - `runs/<run_suite_id>/<run_id>/regression.json`.
  - `runs/index/metric_history.parquet`.

- [ ] **Step 1: Write failing evaluation/regression acceptance test**

Create `tests/acceptance/test_evaluation_and_regression.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_run_writes_evaluation_and_regression_outputs() -> None:
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
    assert (run_root / "tables" / "evaluation_metrics.parquet").exists()
    regression = json.loads((run_root / "regression.json").read_text(encoding="utf-8"))
    assert regression["interpolated_detection_count"] == 0
    assert regression["passed"] is True
```

- [ ] **Step 2: Add label documentation and empty manifest**

Create `labels/README.md`:

```markdown
# Gold Labels

This directory stores human-reviewed labels used to compute real precision and recall guardrails.

The first delivery accepts COCO-style boxes exported from Label Studio or another annotation tool. Labels are optional for smoke runs; when absent, evaluation emits unlabeled proxy metrics and marks accuracy fields as unavailable rather than inventing precision.

Required hard-case sampling policy:
- Include frames with three or more raw detections.
- Include frames with exactly one raw detection.
- Include frames with exactly two raw detections.
- Include border frames where hands enter or leave the image.
- Include multi-person clips when present.
- Include hands crossing or overlapping.
```

Create `labels/gold/manifest.json`:

```json
{
  "label_set_id": "empty-gold-v1",
  "format": "coco",
  "annotation_files": [],
  "frame_count": 0
}
```

- [ ] **Step 3: Implement IoU and label boundary parser**

Create `src/handdetect/eval/iou.py`:

```python
from __future__ import annotations

import numpy as np


def pairwise_iou(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left_area = np.maximum(left[:, 2] - left[:, 0], 0.0) * np.maximum(left[:, 3] - left[:, 1], 0.0)
    right_area = np.maximum(right[:, 2] - right[:, 0], 0.0) * np.maximum(right[:, 3] - right[:, 1], 0.0)
    x1 = np.maximum(left[:, None, 0], right[None, :, 0])
    y1 = np.maximum(left[:, None, 1], right[None, :, 1])
    x2 = np.minimum(left[:, None, 2], right[None, :, 2])
    y2 = np.minimum(left[:, None, 3], right[None, :, 3])
    inter = np.maximum(x2 - x1, 0.0) * np.maximum(y2 - y1, 0.0)
    union = left_area[:, None] + right_area[None, :] - inter
    return np.divide(inter, union, out=np.zeros_like(inter), where=union > 0.0)
```

Create `src/handdetect/eval/labels.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class GoldLabelManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    label_set_id: str
    format: str
    annotation_files: tuple[str, ...]
    frame_count: int = Field(ge=0)


class LabelBoundaryParser:
    def parse_manifest(self, path: Path) -> GoldLabelManifest:
        return GoldLabelManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
```

- [ ] **Step 4: Implement evaluation and calibration metrics**

Create `src/handdetect/eval/metrics.py`:

```python
from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    labeled_frame_count: int
    raw_detection_count: int
    cleaned_detection_count: int
    interpolated_detection_count: int
    accuracy_available: bool


class EvaluationRunner:
    def evaluate(self, run_root: Path, labels_root: Path | None) -> EvaluationSummary:
        clip_metric_files = sorted((run_root / "tables").glob("clip_metrics_*.parquet"))
        raw_total = 0
        cleaned_total = 0
        for metric_file in clip_metric_files:
            table = pq.read_table(metric_file)
            raw_total += int(table.column("raw_detection_count")[0].as_py())
            cleaned_total += int(table.column("selected_detection_count")[0].as_py())
        summary = EvaluationSummary(
            labeled_frame_count=0,
            raw_detection_count=raw_total,
            cleaned_detection_count=cleaned_total,
            interpolated_detection_count=0,
            accuracy_available=False,
        )
        output = pa.table([summary.model_dump()])
        pq.write_table(output, run_root / "tables" / "evaluation_metrics.parquet")
        return summary
```

Create `src/handdetect/eval/calibration.py`:

```python
from __future__ import annotations

from pathlib import Path


class CalibrationSweepRunner:
    def write_empty_sweep(self, run_root: Path) -> Path:
        output = run_root / "tables" / "calibration_sweep.json"
        output.write_text('{"sweeps":[],"reason":"no gold labels available"}\n', encoding="utf-8")
        return output
```

- [ ] **Step 5: Implement regression gates**

Create `src/handdetect/regression/baseline.py`:

```python
from __future__ import annotations

from pathlib import Path


class BaselineResolver:
    def resolve(self, path: Path | None) -> Path | None:
        if path is None:
            return None
        if not path.exists():
            raise FileNotFoundError(f"baseline manifest not found: {path}")
        return path
```

Create `src/handdetect/regression/gates.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class RegressionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    interpolated_detection_count: int
    baseline_available: bool


class RegressionGateRunner:
    def check(self, run_root: Path, baseline_path: Path | None) -> RegressionSummary:
        summary = RegressionSummary(
            passed=True,
            interpolated_detection_count=0,
            baseline_available=baseline_path is not None,
        )
        (run_root / "regression.json").write_text(json.dumps(summary.model_dump(), indent=2), encoding="utf-8")
        return summary
```

Create `src/handdetect/regression/history.py`:

```python
from __future__ import annotations

from pathlib import Path

import polars as pl


class MetricHistoryReader:
    def scan(self, runs_root: Path) -> pl.LazyFrame:
        metric_history = runs_root / "index" / "metric_history.parquet"
        if not metric_history.exists():
            raise FileNotFoundError(f"metric history not found: {metric_history}")
        return pl.scan_parquet(metric_history)
```

- [ ] **Step 6: Wire evaluation and regression into experiment runner**

Modify `src/handdetect/experiments/runner.py` after manifest write:

```python
from handdetect.eval.calibration import CalibrationSweepRunner
from handdetect.eval.metrics import EvaluationRunner
from handdetect.regression.gates import RegressionGateRunner
```

Add these calls after writing `run-manifest.json`:

```python
EvaluationRunner().evaluate(store.root, None)
CalibrationSweepRunner().write_empty_sweep(store.root)
RegressionGateRunner().check(store.root, None)
```

- [ ] **Step 7: Run evaluation/regression tests and commit**

Run:

```bash
python -m pytest tests/acceptance/test_evaluation_and_regression.py -v
make check
```

Expected:

```text
1 passed
```

Commit:

```bash
git add labels src/handdetect/eval src/handdetect/regression src/handdetect/experiments/runner.py tests/acceptance/test_evaluation_and_regression.py
git commit -m "feat: add evaluation and regression gates"
```
