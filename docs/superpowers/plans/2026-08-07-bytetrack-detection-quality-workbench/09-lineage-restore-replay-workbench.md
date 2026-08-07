# Task 9: Lineage Restore, Replay, and One-Button Regression Workbench

**Files:**
- Create: `dvc.yaml`
- Create: `params.yaml`
- Create: `src/handdetect/labels/freeze.py`
- Create: `src/handdetect/lineage/models.py`
- Create: `src/handdetect/lineage/dvc_git.py`
- Create: `src/handdetect/lineage/capture.py`
- Create: `src/handdetect/lineage/replay.py`
- Create: `src/handdetect/workbench/server.py`
- Create: `src/handdetect/workbench/templates/run_detail.html`
- Modify: `src/handdetect/cli/main.py`
- Modify: `src/handdetect/experiments/runner.py`
- Modify: `src/handdetect/tracking_platforms/export_status.py`
- Modify: `src/handdetect/report/static_report.py`
- Modify: `Makefile`
- Create: `tests/acceptance/test_lineage_replay.py`
- Create: `tests/acceptance/test_workbench_replay.py`

**Interfaces:**
- Consumes:
  - Completed run root `runs/<run_suite_id>/<run_id>/`.
  - `RunManifest`, `TrackingExportStatus`, and `ReviewPlatformManifest`.
  - Label Studio project id and API token when freezing labels from a reviewed project.
  - DVC/Git workspace with data, labels, params, configs, and source files tracked.
- Produces:
  - `labels/versions/<label_set_id>/manifest.json`.
  - `runs/<run_suite_id>/<run_id>/lineage/replay.lock.json`.
  - `LineageReplayService.replay(request: ReplayRequest) -> ReplayResult`.
  - `handdetect lineage replay --from-run <suite>/<run> --set key=value`.
  - `handdetect workbench serve` local run page with replay button and status.

## Required User Story

- A reviewer opens a previous run in the local workbench.
- They see the exact lineage proof:
  - source git commit
  - dependency lock hash
  - dataset DVC output hash
  - label-set id and DVC output hash
  - canonical filter config hash
  - MLflow run id
  - DVC experiment ref when available
  - parent/baseline run id
- They edit a small value, for example `adapter.max_center_speed_px_per_s = 3900.0`.
- They click `Replay With Overrides`.
- The system creates an isolated git worktree, restores the exact parent data/labels/config,
  applies the override, runs a child experiment that writes artifacts back to the main `runs/`
  root, compares regression against the parent, and opens the child review journey.
- The current workspace is not checked out, modified, or polluted.

## OSS Ownership Rules

- DVC/Git own exact byte restoration.
- MLflow owns scalar comparison and artifact browsing.
- Label Studio owns human review and annotation export.
- FiftyOne owns visual inspection.
- Evidently owns regression charts.
- `handdetect.workbench` owns only orchestration, typed override validation, and links.

- [ ] **Step 1: Write failing lineage replay acceptance test**

Create `tests/acceptance/test_lineage_replay.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run_smoke() -> tuple[str, str]:
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
    return suite_id, run_id


def test_run_writes_replay_lock_with_restorable_lineage() -> None:
    suite_id, run_id = _run_smoke()
    lock_path = ROOT / "runs" / suite_id / run_id / "lineage" / "replay.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert lock["run_suite_id"] == suite_id
    assert lock["run_id"] == run_id
    assert lock["git"]["commit_sha"]
    assert lock["config"]["sha256"]
    assert lock["dataset"]["content_sha256"]
    assert lock["labels"]["label_set_id"]
    assert lock["tracking"]["mlflow_run_id"] is not None


def test_lineage_replay_creates_child_run_without_overwriting_parent() -> None:
    suite_id, run_id = _run_smoke()
    replay = subprocess.run(
        [
            "python",
            "-m",
            "handdetect.cli.main",
            "lineage",
            "replay",
            "--from-run",
            f"{suite_id}/{run_id}",
            "--set",
            "adapter.max_center_speed_px_per_s=3900.0",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert replay.returncode == 0, replay.stderr
    child_suite = replay.stdout.split("child_suite_id=", 1)[1].split()[0]
    child_run = replay.stdout.split("child_run_id=", 1)[1].split()[0]
    parent_root = ROOT / "runs" / suite_id / run_id
    child_root = ROOT / "runs" / child_suite / child_run
    assert parent_root.exists()
    assert child_root.exists()
    child_lock = json.loads((child_root / "lineage" / "replay.lock.json").read_text())
    assert child_lock["parent"]["run_suite_id"] == suite_id
    assert child_lock["parent"]["run_id"] == run_id
    assert (child_root / "regression.json").exists()
```

- [ ] **Step 2: Add DVC pipeline skeleton**

Create `params.yaml`:

```yaml
handdetect:
  active_config: configs/smoke-experiment.toml
  active_label_set: labels/versions/empty-gold-v1
  runs_root: runs
  dvclive_root: dvclive
```

Create `dvc.yaml`:

```yaml
stages:
  smoke_run:
    cmd: python -m handdetect.cli.main run --config ${handdetect.active_config}
    deps:
      - src/handdetect
      - ${handdetect.active_config}
      - ${handdetect.active_label_set}
      - data
    outs:
      - runs:
          cache: false
    metrics:
      - dvclive:
          cache: false
    params:
      - handdetect.active_config
      - handdetect.active_label_set
```

Run once when implementing this task in a fresh clone:

```bash
dvc init
dvc add data
mkdir -p labels/versions/empty-gold-v1
printf '{"label_set_id":"empty-gold-v1","annotation_sha256":"empty"}\n' \
  > labels/versions/empty-gold-v1/manifest.json
dvc add labels/versions/empty-gold-v1
dvc status
```

Expected:

```text
data.dvc and labels/versions/empty-gold-v1.dvc exist.
```

- [ ] **Step 3: Define lineage models**

Create `src/handdetect/lineage/models.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from handdetect.domain.ids import RunId, RunSuiteId


class GitLineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    commit_sha: str
    dirty_patch_sha256: str | None
    dependency_lock_sha256: str


class ArtifactLineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    logical_name: str
    path: Path
    content_sha256: str
    dvc_hash: str | None


class ConfigLineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    sha256: str
    canonical_toml: str


class LabelLineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    label_set_id: str
    path: Path
    content_sha256: str
    dvc_hash: str | None
    label_studio_project_id: int | None


class TrackingLineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    mlflow_experiment_id: str | None
    mlflow_run_id: str | None
    dvc_experiment_ref: str | None
    evidently_report_path: Path | None


class ParentLineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_suite_id: RunSuiteId
    run_id: RunId
    lineage_id: str


class LineageSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    lineage_id: str
    run_suite_id: RunSuiteId
    run_id: RunId
    git: GitLineageRef
    dataset: ArtifactLineageRef
    labels: LabelLineageRef
    config: ConfigLineageRef
    tracking: TrackingLineageRef
    parent: ParentLineageRef | None


class ParameterOverride(BaseModel):
    model_config = ConfigDict(frozen=True)

    dotted_key: str
    raw_value: str


class ReplayRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_run_suite_id: RunSuiteId
    source_run_id: RunId
    overrides: tuple[ParameterOverride, ...]


class ReplayResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    child_run_suite_id: RunSuiteId
    child_run_id: RunId
    child_lineage_id: str
    regression_path: Path
    review_manifest_path: Path
```

- [ ] **Step 4: Implement Git/DVC command boundary**

Create `src/handdetect/lineage/dvc_git.py`:

```python
from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Sequence
from pathlib import Path

import yaml

from pydantic import BaseModel, ConfigDict


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    stdout: str
    stderr: str


class CommandRunner:
    def run(self, args: Sequence[str], cwd: Path) -> CommandResult:
        completed = subprocess.run(
            list(args),
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            command = " ".join(args)
            raise RuntimeError(f"command failed in {cwd}: {command}\n{completed.stderr}")
        return CommandResult(stdout=completed.stdout, stderr=completed.stderr)


class GitDvcWorkspace:
    def __init__(self, root: Path, runner: CommandRunner) -> None:
        self.root = root
        self.runner = runner

    def commit_sha(self) -> str:
        return self.runner.run(["git", "rev-parse", "HEAD"], self.root).stdout.strip()

    def dirty_patch_sha256(self) -> str | None:
        diff = self.runner.run(["git", "diff", "--binary", "HEAD"], self.root).stdout
        if diff == "":
            return None
        return hashlib.sha256(diff.encode("utf-8")).hexdigest()

    def add_worktree(self, commit_sha: str, path: Path) -> None:
        self.runner.run(["git", "worktree", "add", "--detach", str(path), commit_sha], self.root)

    def dvc_pull(self, worktree: Path) -> None:
        self.runner.run(["dvc", "pull"], worktree)

    def dvc_add(self, path: Path) -> None:
        self.runner.run(["dvc", "add", str(path)], self.root)


class DvcMetadataReader:
    def output_hash(self, dvc_file: Path) -> str | None:
        if not dvc_file.exists():
            return None
        loaded = yaml.safe_load(dvc_file.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"invalid DVC metadata file: {dvc_file}")
        outs = loaded.get("outs")
        if not isinstance(outs, list) or not outs:
            raise ValueError(f"DVC metadata file has no outs: {dvc_file}")
        first = outs[0]
        if not isinstance(first, dict):
            raise ValueError(f"DVC out entry must be an object: {dvc_file}")
        value = first.get("md5") or first.get("hash")
        if value is None:
            return None
        return str(value)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

- [ ] **Step 5: Freeze immutable label versions**

Create `src/handdetect/labels/freeze.py`:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict

from handdetect.lineage.dvc_git import CommandRunner, GitDvcWorkspace


class FrozenLabelSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    label_set_id: str
    path: Path
    manifest_path: Path


class LabelSetFreezer:
    def __init__(self, repo_root: Path, runner: CommandRunner) -> None:
        self.repo_root = repo_root
        self.runner = runner

    def freeze_from_label_studio(
        self,
        base_url: str,
        token: str,
        project_id: int,
    ) -> FrozenLabelSet:
        export_url = (
            f"{base_url.rstrip('/')}/api/projects/{project_id}/export"
            "?exportType=JSON&download_all_tasks=true"
        )
        request = Request(export_url, headers={"Authorization": f"Token {token}"})
        with urlopen(request, timeout=120) as response:
            exported = json.loads(response.read().decode("utf-8"))
        canonical = json.dumps(exported, sort_keys=True, separators=(",", ":"))
        label_set_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
        root = self.repo_root / "labels" / "versions" / label_set_id
        root.mkdir(parents=True, exist_ok=False)
        annotations_path = root / "annotations.json"
        manifest_path = root / "manifest.json"
        annotations_path.write_text(canonical + "\n", encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "label_set_id": label_set_id,
                    "label_studio_project_id": project_id,
                    "annotation_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        GitDvcWorkspace(self.repo_root, self.runner).dvc_add(root)
        return FrozenLabelSet(label_set_id=label_set_id, path=root, manifest_path=manifest_path)
```

- [ ] **Step 6: Extend tracking status with native platform ids**

Modify `src/handdetect/tracking_platforms/export_status.py`:

```python
class PlatformStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    path: str
    error: str | None
    native_id: str | None
```

Update MLflow tracking export so `native_id` is the MLflow run id. Update DVC export so
`native_id` is the DVC experiment ref when the run executes under `dvc exp run`; direct CLI
runs must set it to `None` and still write the replay lock.

- [ ] **Step 7: Capture replay lock for every run**

Create `src/handdetect/lineage/capture.py`:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from handdetect.domain.ids import RunId, RunSuiteId
from handdetect.lineage.dvc_git import (
    CommandRunner,
    DvcMetadataReader,
    GitDvcWorkspace,
    file_sha256,
)
from handdetect.lineage.models import (
    ArtifactLineageRef,
    ConfigLineageRef,
    GitLineageRef,
    LabelLineageRef,
    LineageSnapshot,
    ParentLineageRef,
    TrackingLineageRef,
)


class LineageSnapshotWriter:
    def __init__(self, repo_root: Path, runner: CommandRunner) -> None:
        self.repo_root = repo_root
        self.runner = runner

    def write(
        self,
        run_root: Path,
        suite_id: RunSuiteId,
        run_id: RunId,
        config_path: Path,
        label_set_path: Path,
        parent: ParentLineageRef | None,
    ) -> LineageSnapshot:
        config_text = config_path.read_text(encoding="utf-8")
        workspace = GitDvcWorkspace(self.repo_root, self.runner)
        dvc = DvcMetadataReader()
        tracking = self._tracking_status(run_root)
        lineage_seed = f"{suite_id}:{run_id}:{file_sha256(config_path)}"
        snapshot = LineageSnapshot(
            lineage_id=hashlib.sha256(lineage_seed.encode("utf-8")).hexdigest()[:24],
            run_suite_id=suite_id,
            run_id=run_id,
            git=GitLineageRef(
                commit_sha=workspace.commit_sha(),
                dirty_patch_sha256=workspace.dirty_patch_sha256(),
                dependency_lock_sha256=self._lock_hash(),
            ),
            dataset=ArtifactLineageRef(
                logical_name="assignment-data",
                path=Path("data"),
                content_sha256=self._tree_hash(self.repo_root / "data"),
                dvc_hash=dvc.output_hash(self.repo_root / "data.dvc"),
            ),
            labels=LabelLineageRef(
                label_set_id=label_set_path.name,
                path=label_set_path,
                content_sha256=self._tree_hash(label_set_path),
                dvc_hash=dvc.output_hash(label_set_path.with_suffix(".dvc")),
                label_studio_project_id=None,
            ),
            config=ConfigLineageRef(
                path=config_path,
                sha256=file_sha256(config_path),
                canonical_toml=config_text,
            ),
            tracking=TrackingLineageRef(
                mlflow_experiment_id=tracking.get("mlflow_experiment_id"),
                mlflow_run_id=tracking.get("mlflow_run_id"),
                dvc_experiment_ref=tracking.get("dvc_experiment_ref"),
                evidently_report_path=run_root / "report" / "evidently.html",
            ),
            parent=parent,
        )
        output = run_root / "lineage" / "replay.lock.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        return snapshot

    def _tracking_status(self, run_root: Path) -> dict[str, str | None]:
        status_path = run_root / "tracking_export_status.json"
        if not status_path.exists():
            return {
                "mlflow_experiment_id": None,
                "mlflow_run_id": None,
                "dvc_experiment_ref": None,
            }
        status = json.loads(status_path.read_text(encoding="utf-8"))
        return {
            "mlflow_experiment_id": status.get("mlflow", {}).get("experiment_id"),
            "mlflow_run_id": status.get("mlflow", {}).get("native_id"),
            "dvc_experiment_ref": status.get("dvc", {}).get("native_id"),
        }

    def _lock_hash(self) -> str:
        candidates = [self.repo_root / "uv.lock", self.repo_root / "pyproject.toml"]
        existing = [path for path in candidates if path.exists()]
        digest = hashlib.sha256()
        for path in existing:
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def _tree_hash(self, root: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()
```

- [ ] **Step 8: Implement isolated replay service**

Create `src/handdetect/lineage/replay.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import tomlkit

from handdetect.domain.ids import RunId, RunSuiteId
from handdetect.lineage.dvc_git import CommandRunner, GitDvcWorkspace
from handdetect.lineage.models import LineageSnapshot, ReplayRequest, ReplayResult


class LineageReplayService:
    def __init__(self, repo_root: Path, runner: CommandRunner) -> None:
        self.repo_root = repo_root
        self.runner = runner

    def replay(self, request: ReplayRequest) -> ReplayResult:
        source_root = self.repo_root / "runs" / str(request.source_run_suite_id)
        source_run_root = source_root / str(request.source_run_id)
        snapshot = LineageSnapshot.model_validate_json(
            (source_run_root / "lineage" / "replay.lock.json").read_text(encoding="utf-8")
        )
        replay_root = self.repo_root / ".handdetect" / "replays" / snapshot.lineage_id
        worktree = replay_root / "worktree"
        replay_root.mkdir(parents=True, exist_ok=True)
        GitDvcWorkspace(self.repo_root, self.runner).add_worktree(snapshot.git.commit_sha, worktree)
        GitDvcWorkspace(worktree, self.runner).dvc_pull(worktree)
        child_config = worktree / "configs" / f"replay-{snapshot.lineage_id}.toml"
        child_config.write_text(
            self._apply_overrides(snapshot, request, worktree),
            encoding="utf-8",
        )
        result = self.runner.run(
            [
                "python",
                "-m",
                "handdetect.cli.main",
                "run",
                "--config",
                str(child_config.relative_to(worktree)),
                "--baseline-run",
                f"{request.source_run_suite_id}/{request.source_run_id}",
            ],
            worktree,
        )
        child_suite = RunSuiteId(result.stdout.split("suite_id=", 1)[1].split()[0])
        child_run = RunId(result.stdout.split("run_id=", 1)[1].split()[0])
        child_root = self.repo_root / "runs" / str(child_suite) / str(child_run)
        return ReplayResult(
            child_run_suite_id=child_suite,
            child_run_id=child_run,
            child_lineage_id=self._read_child_lineage(child_root),
            regression_path=child_root / "regression.json",
            review_manifest_path=child_root / "review" / "platforms.json",
        )

    def _apply_overrides(
        self,
        snapshot: LineageSnapshot,
        request: ReplayRequest,
        worktree: Path,
    ) -> str:
        document = tomlkit.parse(snapshot.config.canonical_toml)
        runtime = document["runtime"]
        runtime["data_root"] = str(worktree / "data")
        runtime["runs_root"] = str(self.repo_root / "runs")
        runtime["mlflow_tracking_uri"] = str(self.repo_root / "mlruns")
        runtime["dvclive_root"] = str(self.repo_root / "dvclive")
        for override in request.overrides:
            parts = override.dotted_key.split(".")
            table = document
            for part in parts[:-1]:
                table = table[part]
            table[parts[-1]] = json.loads(override.raw_value)
        return tomlkit.dumps(document)

    def _read_child_lineage(self, child_root: Path) -> str:
        lock = LineageSnapshot.model_validate_json(
            (child_root / "lineage" / "replay.lock.json").read_text(encoding="utf-8")
        )
        return lock.lineage_id
```

- [ ] **Step 9: Add CLI commands**

Modify `src/handdetect/cli/main.py`:

```python
lineage_app = typer.Typer(no_args_is_help=True)
workbench_app = typer.Typer(no_args_is_help=True)
app.add_typer(lineage_app, name="lineage")
app.add_typer(workbench_app, name="workbench")


@lineage_app.command("replay")
def lineage_replay(
    from_run: str,
    set_values: list[str] | None = typer.Option(default=None, "--set"),
) -> None:
    suite_id, run_id = from_run.split("/", 1)
    raw_overrides = [] if set_values is None else set_values
    overrides = tuple(
        ParameterOverride(dotted_key=value.split("=", 1)[0], raw_value=value.split("=", 1)[1])
        for value in raw_overrides
    )
    result = LineageReplayService(Path.cwd(), CommandRunner()).replay(
        ReplayRequest(
            source_run_suite_id=RunSuiteId(suite_id),
            source_run_id=RunId(run_id),
            overrides=overrides,
        )
    )
    typer.echo(f"child_suite_id={result.child_run_suite_id}")
    typer.echo(f"child_run_id={result.child_run_id}")
    typer.echo(f"review={result.review_manifest_path}")


@workbench_app.command("serve")
def workbench_serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    uvicorn.run(create_app(Path.cwd()), host=host, port=port)
```

- [ ] **Step 10: Add one-button local workbench**

Create `src/handdetect/workbench/server.py`:

```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from handdetect.domain.ids import RunId, RunSuiteId
from handdetect.lineage.dvc_git import CommandRunner
from handdetect.lineage.models import ParameterOverride, ReplayRequest
from handdetect.lineage.replay import LineageReplayService


def create_app(repo_root: Path) -> FastAPI:
    app = FastAPI(title="HandDetect Lineage Workbench")
    templates = Jinja2Templates(directory=repo_root / "src" / "handdetect" / "workbench" / "templates")

    @app.get("/runs/{suite_id}/{run_id}", response_class=HTMLResponse)
    def run_detail(request: Request, suite_id: str, run_id: str) -> HTMLResponse:
        lock_path = repo_root / "runs" / suite_id / run_id / "lineage" / "replay.lock.json"
        return templates.TemplateResponse(
            request,
            "run_detail.html",
            {"suite_id": suite_id, "run_id": run_id, "lock_path": lock_path},
        )

    @app.post("/runs/{suite_id}/{run_id}/replay")
    def replay(suite_id: str, run_id: str, override: str = Form(...)) -> RedirectResponse:
        key, value = override.split("=", 1)
        result = LineageReplayService(repo_root, CommandRunner()).replay(
            ReplayRequest(
                source_run_suite_id=RunSuiteId(suite_id),
                source_run_id=RunId(run_id),
                overrides=(ParameterOverride(dotted_key=key, raw_value=value),),
            )
        )
        return RedirectResponse(
            f"/runs/{result.child_run_suite_id}/{result.child_run_id}",
            status_code=303,
        )

    return app
```

Create `src/handdetect/workbench/templates/run_detail.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>HandDetect Run {{ suite_id }}/{{ run_id }}</title>
  </head>
  <body>
    <main>
      <h1>Run {{ suite_id }}/{{ run_id }}</h1>
      <p>Lineage lock: <code>{{ lock_path }}</code></p>
      <form method="post" action="/runs/{{ suite_id }}/{{ run_id }}/replay">
        <label for="override">Override</label>
        <input
          id="override"
          name="override"
          value="adapter.max_center_speed_px_per_s=3900.0"
        >
        <button type="submit">Replay With Overrides</button>
      </form>
    </main>
  </body>
</html>
```

- [ ] **Step 11: Wire Makefile and report links**

Modify `Makefile`:

```make
lineage-replay:
	$(PYTHON) -m handdetect.cli.main lineage replay --from-run $(run) --set $(set)

workbench:
	$(PYTHON) -m handdetect.cli.main workbench serve
```

Modify `src/handdetect/report/static_report.py` so the report links to:

```html
<a href="../../lineage/replay.lock.json">Replay lock</a>
<p>Open the local workbench and visit <code>/runs/{suite_id}/{run_id}</code>.</p>
```

- [ ] **Step 12: Test workbench replay button**

Create `tests/acceptance/test_workbench_replay.py`:

```python
from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from handdetect.workbench.server import create_app


ROOT = Path(__file__).resolve().parents[2]


def test_workbench_run_page_contains_replay_button() -> None:
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
    client = TestClient(create_app(ROOT))
    response = client.get(f"/runs/{suite_id}/{run_id}")
    assert response.status_code == 200
    assert "Replay With Overrides" in response.text
    assert "lineage/replay.lock.json" in response.text
```

- [ ] **Step 13: Run verification and commit**

Run:

```bash
python -m pytest tests/acceptance/test_lineage_replay.py -v
python -m pytest tests/acceptance/test_workbench_replay.py -v
make verify
```

Expected:

```text
passed
```

Commit:

```bash
git add dvc.yaml params.yaml src/handdetect/labels src/handdetect/lineage
git add src/handdetect/workbench src/handdetect/cli/main.py
git add src/handdetect/experiments/runner.py src/handdetect/tracking_platforms
git add src/handdetect/report/static_report.py
git add Makefile tests/acceptance/test_lineage_replay.py
git add tests/acceptance/test_workbench_replay.py
git commit -m "feat: add lineage restore and replay workbench"
```
