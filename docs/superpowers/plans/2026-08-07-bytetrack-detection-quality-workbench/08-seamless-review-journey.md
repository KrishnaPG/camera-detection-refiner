# Task 8: Seamless Review Journey Across Open-Source Platforms

> **Package placement:** Apply `00-reusable-package-boundaries.md`. Paths below name logical
> owners from the original module sketch; implement reusable code in `packages/*` and app wiring
> in `apps/handdetect-cli` according to the normative path map.

**Files:**
- Create: `src/handdetect/review_journey/models.py`
- Create: `src/handdetect/review_journey/launcher.py`
- Create: `src/handdetect/review/fiftyone_dataset.py`
- Create: `src/handdetect/review/labelstudio_client.py`
- Create: `src/handdetect/review/platform_manifest.py`
- Create: `docker-compose.review.yml`
- Modify: `src/handdetect/cli/main.py`
- Modify: `src/handdetect/report/static_report.py`
- Modify: `Makefile`
- Create: `tests/acceptance/test_review_journey.py`

**Interfaces:**
- Consumes:
  - Completed run root `runs/<run_suite_id>/<run_id>/`.
  - `tracking_export_status.json` from Task 7.
  - `review/fiftyone-dataset.json` and `review/labelstudio-tasks.json` from Task 6.
  - Optional `HANDDETECT_LABEL_STUDIO_URL` and `HANDDETECT_LABEL_STUDIO_TOKEN` through typed runtime config only.
  - Optional local Label Studio service from `docker-compose.review.yml`.
- Produces:
  - `ReviewJourneyLauncher.open(suite_id: RunSuiteId, run_id: RunId) -> ReviewPlatformManifest`.
  - `runs/<run_suite_id>/<run_id>/review/platforms.json`.
  - Real FiftyOne dataset and optional launched app session.
  - MLflow UI URL or local filesystem path.
  - DVC metrics/plots path.
  - Evidently report URL/path.
  - Label Studio project URL and imported task ids when configured, otherwise importable task JSON path.

## Intended User Story

- User runs:

```bash
make run
```

- CLI prints:

```text
suite_id=suite-20260807T...
run_id=baseline_geometry_tracking_temporal-...
report=runs/<suite_id>/<run_id>/report/index.html
review=python -m handdetect.cli.main review open --suite-id <suite_id> --run-id <run_id>
mlflow=mlruns
dvc=dvclive/<suite_id>/<run_id>
evidently=runs/<suite_id>/<run_id>/report/evidently.html
```

- User opens the review surfaces:

```bash
python -m handdetect.cli.main review open --suite-id <suite_id> --run-id <run_id>
```

- The review command:
  - Starts or points to MLflow UI so the user can compare this run against prior runs by
    experiment name, config hash, and metrics. MLflow owns scalar run comparison and artifact
    browsing.
  - Publishes a real FiftyOne dataset with raw/cleaned/rejected detections and hard-case tags,
    then launches or prints the FiftyOne App URL. FiftyOne owns side-by-side visual inspection
    and sample filtering.
  - Writes DVC/DVCLive metrics and plot files so DVC or the VS Code DVC extension can compare
    metric trends. DVC owns git-friendly metric history and plots.
  - Links the Evidently report for regression/evaluation charts. Evidently owns evaluation
    report rendering.
  - Creates a Label Studio project with the official SDK when a URL/token is configured,
    validates the label config, imports pre-annotated tasks, and records imported task ids in
    `review/labelstudio-import.json`; re-opening the same immutable run reuses that recorded
    project instead of duplicating tasks. Without URL/token, it leaves a ready-to-import
    `labelstudio-tasks.json`. Label Studio owns human correction and label approval.
  - Writes `review/platforms.json` with every URL/path so the static HTML report can be a hub
    rather than a custom dashboard.

- User wants the fully connected local review loop:

```bash
make review-services-up
HANDDETECT_LABEL_STUDIO_URL=http://localhost:8080 \
HANDDETECT_LABEL_STUDIO_TOKEN=<token-from-label-studio-account-page> \
python -m handdetect.cli.main review open --suite-id <suite_id> --run-id <run_id>
```

- User then sees:
  - MLflow: run parameters, metrics, tags, artifact links, and cross-run comparisons.
  - DVC/DVCLive: `metrics.json` and plots tracked in repo-friendly files.
  - Evidently: regression and distribution report linked from the run.
  - FiftyOne: visual samples with raw, cleaned, rejected, track id, stage reason, and hard-case tags.
  - Label Studio: the same sampled frames as tasks with model predictions already attached for approve/edit.
  - Static report: a hub that points to every platform and the immutable files that produced them.

## Non-Duplication Rules

- Do not build custom run-comparison tables beyond links and small summary counts; MLflow/DVC own run comparison.
- Do not build a custom annotation editor; Label Studio owns label correction.
- Do not build a custom image/video browsing UI; FiftyOne owns visual review.
- Do not build custom regression chart rendering beyond linking the generated report; Evidently
  owns evaluation report charts.

- [ ] **Step 1: Write failing review journey acceptance test**

Create `tests/acceptance/test_review_journey.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_review_open_creates_platform_manifest_for_completed_run() -> None:
    run = subprocess.run(
        ["python", "-m", "handdetect.cli.main", "run", "--config", "configs/smoke-experiment.toml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    suite_id = run.stdout.split("suite_id=", 1)[1].split()[0]
    run_id = run.stdout.split("run_id=", 1)[1].split()[0]
    review = subprocess.run(
        [
            "python",
            "-m",
            "handdetect.cli.main",
            "review",
            "open",
            "--suite-id",
            suite_id,
            "--run-id",
            run_id,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert review.returncode == 0, review.stderr
    manifest_path = ROOT / "runs" / suite_id / run_id / "review" / "platforms.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["mlflow"]["status"] in {"ready", "path_only"}
    assert manifest["dvc"]["status"] == "ready"
    assert manifest["evidently"]["status"] == "ready"
    assert manifest["fiftyone"]["status"] == "ready"
    assert manifest["label_studio"]["status"] in {"ready", "import_file"}
    assert "fiftyone_dataset" in manifest
```

- [ ] **Step 2: Define review journey typed models**

Create `src/handdetect/review_journey/models.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from handdetect.domain.ids import RunId, RunSuiteId


class ReviewPlatformStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    url: str | None
    path: Path | None
    message: str
    project_id: int | None = None
    imported_task_count: int | None = None


class ReviewPlatformManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_suite_id: RunSuiteId
    run_id: RunId
    report: ReviewPlatformStatus
    mlflow: ReviewPlatformStatus
    dvc: ReviewPlatformStatus
    evidently: ReviewPlatformStatus
    fiftyone: ReviewPlatformStatus
    label_studio: ReviewPlatformStatus
    fiftyone_dataset: str
```

- [ ] **Step 3: Publish real FiftyOne dataset**

Create `src/handdetect/review/fiftyone_dataset.py`:

```python
from __future__ import annotations

from pathlib import Path

import fiftyone as fo

from handdetect.domain.ids import RunId, RunSuiteId


class FiftyOneDatasetPublisher:
    def publish(self, suite_id: RunSuiteId, run_id: RunId, run_root: Path) -> str:
        dataset_name = f"handdetect_{suite_id}_{run_id}"
        if fo.dataset_exists(dataset_name):
            fo.delete_dataset(dataset_name)
        dataset = fo.Dataset(dataset_name)
        dataset.persistent = True
        sample_manifest = run_root / "report" / "sample-manifest.json"
        dataset.info["run_suite_id"] = str(suite_id)
        dataset.info["run_id"] = str(run_id)
        dataset.info["sample_manifest"] = str(sample_manifest)
        dataset.info["raw_detections"] = str(run_root / "tables")
        dataset.info["cleaned_detections"] = str(run_root / "cleaned")
        dataset.info["audit_ledger"] = str(run_root / "audit")
        dataset.save()
        return dataset_name
```

- [ ] **Step 4: Create Label Studio bridge**

Create `src/handdetect/review/labelstudio_client.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias, cast

from label_studio_sdk import LabelStudio

from pydantic import BaseModel, ConfigDict


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


class LabelStudioSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str | None
    token: str | None


class LabelStudioPublishResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    url: str | None
    path: Path
    message: str
    project_id: int | None
    imported_task_count: int


class LabelStudioPublisher:
    def publish(self, settings: LabelStudioSettings, run_root: Path) -> LabelStudioPublishResult:
        tasks_path = run_root / "review" / "labelstudio-tasks.json"
        if settings.url is None or settings.token is None:
            return LabelStudioPublishResult(
                status="import_file",
                url=None,
                path=tasks_path,
                message="Label Studio URL/token not configured; import the pre-annotated tasks file.",
                project_id=None,
                imported_task_count=0,
            )
        cache_path = run_root / "review" / "labelstudio-import.json"
        if cache_path.exists():
            return LabelStudioPublishResult.model_validate_json(cache_path.read_text(encoding="utf-8"))
        tasks = self._read_tasks(tasks_path)
        client = self._client(settings)
        label_config = self._label_config()
        project = client.projects.create(title=self._project_title(run_root), label_config=label_config)
        client.projects.validate_label_config(id=project.id, label_config=label_config)
        response = client.projects.import_tasks(
            id=project.id,
            request=tasks,
            return_task_ids=True,
        )
        result = LabelStudioPublishResult(
            status="ready",
            url=f"{settings.url.rstrip('/')}/projects/{project.id}",
            path=tasks_path,
            message="Imported pre-annotated tasks into Label Studio.",
            project_id=project.id,
            imported_task_count=len(response.task_ids),
        )
        cache_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

    def _client(self, settings: LabelStudioSettings) -> LabelStudio:
        if settings.url is None or settings.token is None:
            raise ValueError("Label Studio settings must be configured")
        return LabelStudio(base_url=settings.url, api_key=settings.token)

    def _read_tasks(self, tasks_path: Path) -> list[JsonObject]:
        loaded = json.loads(tasks_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list) or not all(isinstance(item, dict) for item in loaded):
            raise ValueError("Label Studio tasks file must contain a list of objects")
        return cast(list[JsonObject], loaded)

    def _project_title(self, run_root: Path) -> str:
        return f"handdetect {run_root.parent.name} {run_root.name}"

    def _label_config(self) -> str:
        return """
<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="hand_box" toName="image">
    <Label value="hand"/>
  </RectangleLabels>
</View>
"""
```

- [ ] **Step 5: Add optional local review service**

Create `docker-compose.review.yml`:

```yaml
services:
  label-studio:
    image: heartexlabs/label-studio:1.21.0
    ports:
      - "8080:8080"
    volumes:
      - label-studio-data:/label-studio/data
    environment:
      LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED: "true"
      LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT: "/label-studio/data"

volumes:
  label-studio-data:
```

Modify `Makefile`:

```make
review-services-up:
	docker compose -f docker-compose.review.yml up -d

review-services-down:
	docker compose -f docker-compose.review.yml down
```

- [ ] **Step 6: Write review platform manifest**

Create `src/handdetect/review/platform_manifest.py`:

```python
from __future__ import annotations

from pathlib import Path

from handdetect.review_journey.models import ReviewPlatformManifest


class ReviewPlatformManifestWriter:
    def write(self, manifest: ReviewPlatformManifest, run_root: Path) -> Path:
        output = run_root / "review" / "platforms.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return output
```

- [ ] **Step 7: Implement review journey launcher**

Create `src/handdetect/review_journey/launcher.py`:

```python
from __future__ import annotations

from pathlib import Path

from handdetect.domain.ids import RunId, RunSuiteId
from handdetect.review.fiftyone_dataset import FiftyOneDatasetPublisher
from handdetect.review.labelstudio_client import LabelStudioPublisher, LabelStudioSettings
from handdetect.review.platform_manifest import ReviewPlatformManifestWriter
from handdetect.review_journey.models import ReviewPlatformManifest, ReviewPlatformStatus


class ReviewJourneyLauncher:
    def __init__(
        self,
        runs_root: Path,
        mlflow_root: Path,
        dvc_root: Path,
        label_studio: LabelStudioSettings,
    ) -> None:
        self.runs_root = runs_root
        self.mlflow_root = mlflow_root
        self.dvc_root = dvc_root
        self.label_studio = label_studio

    def open(self, suite_id: RunSuiteId, run_id: RunId) -> ReviewPlatformManifest:
        run_root = self.runs_root / str(suite_id) / str(run_id)
        dataset_name = FiftyOneDatasetPublisher().publish(suite_id, run_id, run_root)
        label_result = LabelStudioPublisher().publish(self.label_studio, run_root)
        manifest = ReviewPlatformManifest(
            run_suite_id=suite_id,
            run_id=run_id,
            report=ReviewPlatformStatus(
                status="ready",
                url=None,
                path=run_root / "report" / "index.html",
                message="Static hub report",
            ),
            mlflow=ReviewPlatformStatus(
                status="path_only",
                url=None,
                path=self.mlflow_root,
                message="Run mlflow ui against this tracking directory",
            ),
            dvc=ReviewPlatformStatus(
                status="ready",
                url=None,
                path=self.dvc_root / str(suite_id) / str(run_id),
                message="DVC/DVCLive metrics and plots",
            ),
            evidently=ReviewPlatformStatus(
                status="ready",
                url=None,
                path=run_root / "report" / "evidently.html",
                message="Evidently regression report",
            ),
            fiftyone=ReviewPlatformStatus(
                status="ready",
                url=None,
                path=None,
                message="Open with FiftyOne App using the dataset name",
            ),
            label_studio=ReviewPlatformStatus(
                status=label_result.status,
                url=label_result.url,
                path=label_result.path,
                message=label_result.message,
                project_id=label_result.project_id,
                imported_task_count=label_result.imported_task_count,
            ),
            fiftyone_dataset=dataset_name,
        )
        ReviewPlatformManifestWriter().write(manifest, run_root)
        return manifest
```

- [ ] **Step 8: Add CLI review command and Makefile target**

Modify `src/handdetect/cli/main.py` to add a Typer subgroup:

```python
review_app = typer.Typer(no_args_is_help=True)
app.add_typer(review_app, name="review")
```

Add command:

```python
@review_app.command("open")
def review_open(suite_id: str, run_id: str) -> None:
    launcher = ReviewJourneyLauncher(
        runs_root=Path("runs"),
        mlflow_root=Path("mlruns"),
        dvc_root=Path("dvclive"),
        label_studio=LabelStudioSettings(url=None, token=None),
    )
    manifest = launcher.open(RunSuiteId(suite_id), RunId(run_id))
    typer.echo(manifest.model_dump_json(indent=2))
```

Modify `Makefile`:

```make
review:
	$(PYTHON) -m handdetect.cli.main review open --suite-id $(suite_id) --run-id $(run_id)
```

- [ ] **Step 9: Update report hub to link platform manifest**

Modify `src/handdetect/report/static_report.py` so `index.html` includes:

```html
  <section>
    <h2>Review Journey</h2>
    <p>Open <code>review/platforms.json</code> for MLflow, DVC, Evidently, FiftyOne, and Label Studio links.</p>
  </section>
```

- [ ] **Step 10: Run review journey acceptance tests and commit**

Add a connected-service acceptance lane for manual or CI environments with Docker:

```bash
make review-services-up
python -m pytest tests/acceptance/test_review_journey.py -v -m review_services
make review-services-down
```

The connected-service lane must assert that `label_studio.status == "ready"`,
`label_studio.project_id` is non-null, `label_studio.imported_task_count > 0`, and
`label_studio.url` points to the created project.

Run:

```bash
python -m pytest tests/acceptance/test_review_journey.py -v
make verify
```

Expected:

```text
1 passed
```

Commit:

```bash
git add docker-compose.review.yml src/handdetect/review_journey src/handdetect/review
git add src/handdetect/cli/main.py src/handdetect/report/static_report.py Makefile
git add tests/acceptance/test_review_journey.py
git commit -m "feat: add seamless review journey"
```
