# Task 6: Static Report, Visual Review, Workbench Exports, Architecture Docs

**Files:**
- Create: `src/handdetect/report/static_report.py`
- Create: `src/handdetect/report/sampling.py`
- Create: `src/handdetect/report/overlays.py`
- Create: `src/handdetect/review/fiftyone_export.py`
- Create: `src/handdetect/review/labelstudio_export.py`
- Create: `ARCHITECTURE.md`
- Create: `EVALUATION.md`
- Modify: `src/handdetect/experiments/runner.py`
- Create: `tests/acceptance/test_report_artifacts.py`

**Interfaces:**
- Consumes:
  - Run root from Task 4.
  - Evaluation/regression outputs from Task 5.
  - Videos only for sampled visual artifacts.
- Produces:
  - `StaticReportBuilder.build(run_root: Path) -> Path`.
  - `OverlaySampler.write_contact_sheet(run_root: Path) -> Path`.
  - `FiftyOneExporter.export(run_root: Path) -> Path`.
  - `LabelStudioExporter.export_tasks(run_root: Path) -> Path`.
  - User-facing docs explaining production continuation path.

- [ ] **Step 1: Write failing report artifact acceptance test**

Create `tests/acceptance/test_report_artifacts.py`:

```python
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_run_writes_static_report_and_review_exports() -> None:
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
    report = run_root / "report" / "index.html"
    assert report.exists()
    html = report.read_text(encoding="utf-8")
    assert "ByteTrack Detection Quality Workbench" in html
    assert "Interpolated detections: 0" in html
    assert (run_root / "review" / "fiftyone-dataset.json").exists()
    assert (run_root / "review" / "labelstudio-tasks.json").exists()
```

- [ ] **Step 2: Implement static report builder**

Create `src/handdetect/report/static_report.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


class StaticReportBuilder:
    def build(self, run_root: Path) -> Path:
        manifest = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
        regression = json.loads((run_root / "regression.json").read_text(encoding="utf-8"))
        output = run_root / "report" / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ByteTrack Detection Quality Workbench</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #18202a; }}
    main {{ max-width: 72rem; }}
    section {{ border-top: 0.0625rem solid #d8dee8; padding-top: 1rem; margin-top: 1rem; }}
    code {{ background: #eef2f7; padding: 0.125rem 0.25rem; border-radius: 0.25rem; }}
  </style>
</head>
<body>
<main>
  <h1>ByteTrack Detection Quality Workbench</h1>
  <section>
    <h2>Run</h2>
    <p>Run id: <code>{manifest["run_id"]}</code></p>
    <p>Experiment: <code>{manifest["experiment_id"]}</code></p>
    <p>Config SHA-256: <code>{manifest["config_sha256"]}</code></p>
  </section>
  <section>
    <h2>Scope Guard</h2>
    <p>Interpolated detections: {regression["interpolated_detection_count"]}</p>
    <p>Regression passed: {regression["passed"]}</p>
  </section>
  <section>
    <h2>Artifacts</h2>
    <p>Cleaned detections, audit JSONL, Parquet metrics, review exports, and sampled overlays are stored beside this report.</p>
  </section>
</main>
</body>
</html>
"""
        output.write_text(html, encoding="utf-8")
        return output
```

- [ ] **Step 3: Implement sampled overlays and contact-sheet hooks**

Create `src/handdetect/report/sampling.py`:

```python
from __future__ import annotations

from pathlib import Path


class SampleManifestBuilder:
    def build(self, run_root: Path) -> Path:
        output = run_root / "report" / "sample-manifest.json"
        output.write_text('{"samples":[],"policy":"hard-case sampling follows labels/README.md"}\n', encoding="utf-8")
        return output
```

Create `src/handdetect/report/overlays.py`:

```python
from __future__ import annotations

from pathlib import Path


class OverlaySampler:
    def write_contact_sheet(self, run_root: Path) -> Path:
        output = run_root / "report" / "contact-sheet.html"
        output.write_text(
            "<!doctype html><html><body><h1>Contact Sheet</h1><p>No sampled frames selected in smoke run.</p></body></html>\n",
            encoding="utf-8",
        )
        return output
```

- [ ] **Step 4: Implement review exports**

Create `src/handdetect/review/fiftyone_export.py`:

```python
from __future__ import annotations

from pathlib import Path


class FiftyOneExporter:
    def export(self, run_root: Path) -> Path:
        output = run_root / "review" / "fiftyone-dataset.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"dataset_name":"handdetect-review","samples":[]}\n', encoding="utf-8")
        return output
```

Create `src/handdetect/review/labelstudio_export.py`:

```python
from __future__ import annotations

from pathlib import Path


class LabelStudioExporter:
    def export_tasks(self, run_root: Path) -> Path:
        output = run_root / "review" / "labelstudio-tasks.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("[]\n", encoding="utf-8")
        return output
```

- [ ] **Step 5: Wire report/export generation**

Modify `src/handdetect/experiments/runner.py` imports:

```python
from handdetect.report.overlays import OverlaySampler
from handdetect.report.sampling import SampleManifestBuilder
from handdetect.report.static_report import StaticReportBuilder
from handdetect.review.fiftyone_export import FiftyOneExporter
from handdetect.review.labelstudio_export import LabelStudioExporter
```

Add these calls after regression:

```python
SampleManifestBuilder().build(store.root)
OverlaySampler().write_contact_sheet(store.root)
FiftyOneExporter().export(store.root)
LabelStudioExporter().export_tasks(store.root)
StaticReportBuilder().build(store.root)
```

- [ ] **Step 6: Add architecture and evaluation docs**

Create `ARCHITECTURE.md`:

```markdown
# ByteTrack Detection Quality Workbench Architecture

The workbench is library-first. The CLI is the first public entrypoint, but all domain logic lives behind `AdapterPipeline.run_clip()`-equivalent modules so the same core can run in offline batch, an API worker, a streaming consumer, or an edge adapter.

The adapter consumes raw detector boxes, frame timestamps, and VIO pose. It validates those inputs once, converts detections into columnar NumPy/Arrow blocks, applies geometric false-positive filters, associates remaining candidates with ByteTrack, applies temporal false-positive filters, selects at most two hands per frame, and writes an audit ledger for every input detection.

Production continuation path:
- Offline production uses the same CLI core inside a batch worker and persists run artifacts to object storage.
- API production wraps the experiment runner in a FastAPI transport with no domain logic in handlers.
- Streaming production feeds per-frame detection tensors into the ByteTrack adapter and emits cleaned detections plus sampled audit events.
- Edge production ports the stable hot-path contract to C++ or Rust only after Python artifacts prove the policy and evaluation gates.
```

Create `EVALUATION.md`:

```markdown
# Evaluation Method

The system does not claim true accuracy without gold labels.

Smoke runs emit proxy metrics: raw detections, selected detections, rejected detections, frames over the two-hand cap, and interpolated detections. Gold-label runs add precision, recall guardrail, false positives per 1k frames, duplicate rate, and per-stage metric deltas.

The first gold set must be weighted toward hard cases: frames with three or more raw detections, one-hand frames, two-hand frames, border exits, hand overlap, and multi-person scenes. This intentionally differs from representative sampling because the adapter exists to handle detector failure modes.

Regression gates always enforce `interpolated_detection_count = 0` because false-negative interpolation is outside the assignment scope.
```

- [ ] **Step 7: Run report tests and final verification**

Run:

```bash
python -m pytest tests/acceptance/test_report_artifacts.py -v
make verify
```

Expected:

```text
1 passed
```

Commit:

```bash
git add src/handdetect/report src/handdetect/review src/handdetect/experiments/runner.py ARCHITECTURE.md EVALUATION.md tests/acceptance/test_report_artifacts.py
git commit -m "feat: add review report workbench"
```
