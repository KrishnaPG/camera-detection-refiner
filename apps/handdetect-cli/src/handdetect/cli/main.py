from __future__ import annotations

import json
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer
from dq_contracts.ids import RunId, RunSuiteId
from handdetect.experiments.runner import ExperimentRunner
from handdetect.io.dataset import DatasetScanner
from handdetect.labels.freeze import LabelSetFreezer
from handdetect.lineage.capture import LineageSnapshotWriter
from handdetect.lineage.replay import LineageReplayService
from handdetect.report.overlays import OverlaySampler
from handdetect.report.sampling import SampleManifestBuilder
from handdetect.review.fiftyone_export import FiftyOneExporter
from handdetect.review.labelstudio_export import LabelStudioExporter
from handdetect.review.story_artifacts import StoryArtifactBuilder
from handdetect.review_journey.launcher import ReviewJourneyLauncher
from handdetect.runs.ids import RunSuiteIdProvider
from handdetect.runs.manifest import SeedManifest
from handdetect.runs.store import SeedManifestWriter
from handdetect.runtime_config import parse_config_with_runtime_env
from handdetect.runtime_paths import dvclive_root, mlflow_root, runs_root, runtime_state_root
from handdetect.workbench.server import serve
from handdetect_domain.config import RuntimeConfig

app = typer.Typer(no_args_is_help=True)
review_app = typer.Typer(no_args_is_help=True)
lineage_app = typer.Typer(no_args_is_help=True)
workbench_app = typer.Typer(no_args_is_help=True)
app.add_typer(review_app, name="review")
app.add_typer(lineage_app, name="lineage")
app.add_typer(workbench_app, name="workbench")

RunConfigOption = Annotated[Path, typer.Option(exists=True, readable=True)]
SmokeConfigOption = Annotated[Path, typer.Option("--config", exists=True, readable=True)]
FromRunOption = Annotated[str, typer.Option("--from-run")]
ReplayOverrideOption = Annotated[list[str] | None, typer.Option("--set")]


@app.command()
def doctor() -> None:
    data_root = Path("data")
    current_runs_root = runs_root()
    clip_count = len(DatasetScanner().scan(data_root))
    typer.echo(
        f"handdetect doctor data_root={data_root} runs_root={current_runs_root} clips={clip_count}"
    )


@app.command()
def seed(data_root: Path = Path("data"), out: Path | None = None) -> None:
    output = out or runs_root() / "seed" / "seed-manifest.json"
    clips = DatasetScanner().scan(data_root)
    manifest = SeedManifest(
        dataset_root=data_root,
        dataset_file_count=sum(1 for path in data_root.rglob("*") if path.is_file()),
        clip_count=len(clips),
        smoke_clip_ids=tuple(clip.clip_id for clip in clips[:3]),
    )
    SeedManifestWriter().write(manifest, output)
    typer.echo(f"seed_manifest={output}")


@app.command()
def run(config: RunConfigOption) -> None:
    run_experiment_suite(config, open_review=False)


@app.command("run-smoke-experiment")
def run_smoke_experiment(
    config: SmokeConfigOption = Path("configs/smoke-experiment.toml"),
) -> None:
    run_experiment_suite(config, open_review=True)


def run_experiment_suite(config: Path, open_review: bool) -> list[tuple[RunSuiteId, RunId]]:
    parsed = parse_config_with_runtime_env(config)
    suite_id = RunSuiteIdProvider().create()
    with progress_phase("pipeline", "adapter_experiment"):
        run_ids = ExperimentRunner().run(parsed, suite_id, config)
    created_runs: list[tuple[RunSuiteId, RunId]] = []
    for run_id in run_ids:
        run_root = parsed.runtime.runs_root / str(suite_id) / str(run_id)
        with progress_phase("samples", f"sample_manifest run_id={run_id}"):
            SampleManifestBuilder().build(run_root)
            OverlaySampler().write_contact_sheet(run_root)
        with progress_phase("fiftyone_manifest", f"fiftyone_manifest run_id={run_id}"):
            FiftyOneExporter().export(run_root)
        with progress_phase("label_studio_export", f"label_studio_export run_id={run_id}"):
            LabelStudioExporter().export_tasks(run_root)
        with progress_phase("story_media", f"story_review_media run_id={run_id}"):
            StoryArtifactBuilder().build(run_root, parsed.runtime.workbench_public_url or "")
        with progress_phase("lineage", f"lineage_snapshot run_id={run_id}"):
            StaticLineage().capture(parsed.runtime, run_root, suite_id, run_id, config)
        if open_review:
            with progress_phase("review_platforms", f"review_platforms run_id={run_id}"):
                ReviewJourneyLauncher().open(
                    suite_id,
                    run_id,
                    parsed.runtime,
                    run_root,
                )
        created_runs.append((suite_id, run_id))
        typer.echo(
            f"suite_id={suite_id} run_id={run_id} report={run_root / 'report' / 'index.html'}"
        )
    return created_runs


@contextmanager
def progress_phase(phase: str, message: str) -> Iterator[None]:
    start = time.perf_counter()
    emit_progress(phase, "running", message)
    try:
        yield
    except Exception as exc:
        elapsed_seconds = time.perf_counter() - start
        emit_progress(
            phase,
            "failed",
            f"{message} error={type(exc).__name__} elapsed_seconds={elapsed_seconds:.3f}",
        )
        raise
    elapsed_seconds = time.perf_counter() - start
    emit_progress(phase, "complete", f"{message} elapsed_seconds={elapsed_seconds:.3f}")


def emit_progress(phase: str, status: str, message: str) -> None:
    typer.echo(f"progress phase={phase} status={status} message={message}")


class StaticLineage:
    def capture(
        self,
        runtime: RuntimeConfig,
        run_root: Path,
        suite_id: RunSuiteId,
        run_id: RunId,
        config: Path,
    ) -> None:
        LineageSnapshotWriter().write(
            run_root=run_root,
            suite_id=suite_id,
            run_id=run_id,
            config_path=config,
            data_root=runtime.data_root,
            label_set_path=Path("labels") / "versions" / "empty-gold-v1",
        )


@app.command()
def migrate() -> None:
    mlflow_root().mkdir(parents=True, exist_ok=True)
    dvclive_root().mkdir(parents=True, exist_ok=True)
    runtime_state_root().mkdir(parents=True, exist_ok=True)
    typer.echo("migrate complete")


@app.command()
def clean(
    runs_root_path: Annotated[
        Path | None,
        typer.Option("--runs-root", "--runs-root-path"),
    ] = None,
) -> None:
    target_runs_root = runs_root_path or runs_root()
    for target in [target_runs_root, dvclive_root(), runtime_state_root()]:
        if target.exists():
            shutil.rmtree(target)
    typer.echo(f"cleaned={target_runs_root}")


@review_app.command("open")
def review_open(
    suite_id: str = typer.Option(..., "--suite-id"),
    run_id: str = typer.Option(..., "--run-id"),
) -> None:
    run_root = runs_root() / suite_id / run_id
    config_path = Path(run_root / "run-manifest.json")
    manifest = json.loads(config_path.read_text(encoding="utf-8"))
    runtime = parse_config_with_runtime_env(Path(manifest["config_path"])).runtime
    platform_manifest = ReviewJourneyLauncher().open(
        RunSuiteId(suite_id),
        RunId(run_id),
        runtime,
        run_root,
    )
    typer.echo(platform_manifest.model_dump_json(indent=2))


@lineage_app.command("replay")
def lineage_replay(
    from_run: FromRunOption,
    set: ReplayOverrideOption = None,
) -> None:
    child_suite, child_run = LineageReplayService().replay(from_run, set or [])
    typer.echo(f"child_suite_id={child_suite} child_run_id={child_run}")


@workbench_app.command("serve")
def workbench_serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    serve(host, port)


@app.command()
def check() -> None:
    typer.echo("handdetect check uses root make target")


@app.command()
def test() -> None:
    typer.echo("handdetect test uses root make target")


@app.command()
def verify() -> None:
    typer.echo("handdetect verify uses root make target")


@app.command()
def freeze_labels(source: Path) -> None:
    output = LabelSetFreezer().freeze_tasks(source)
    typer.echo(f"label_set_manifest={output}")


if __name__ == "__main__":
    app()
