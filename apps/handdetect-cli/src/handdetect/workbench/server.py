from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import uvicorn
from dq_contracts.ids import RunId, RunSuiteId
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from handdetect.lineage.replay import LineageReplayService
from handdetect.review_journey.launcher import ReviewJourneyLauncher
from handdetect.runtime_config import parse_config_with_runtime_env
from handdetect.runtime_paths import runs_root, workbench_job_root

PROGRESS_PHASES: tuple[tuple[str, str], ...] = (
    ("pipeline", "Adapter pipeline"),
    ("samples", "Review samples"),
    ("fiftyone_manifest", "FiftyOne manifest"),
    ("label_studio_export", "Label Studio export"),
    ("story_media", "Story media"),
    ("lineage", "Lineage snapshot"),
    ("review_platforms", "Platform bridge"),
)
PROGRESS_LINE_RE = re.compile(
    r"\bprogress\s+phase=(?P<phase>[a-z0-9_-]+)\s+"
    r"status=(?P<status>[a-z0-9_-]+)\s+message=(?P<message>.*)$"
)


def create_app() -> FastAPI:
    app = FastAPI(title="HandDetect Workbench")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/assets", StaticFiles(directory=str(static_dir)), name="assets")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        runs: list[dict[str, object]] = []
        current_runs_root = runs_root()
        for suite_dir in sorted(current_runs_root.glob("suite-*")):
            for run_dir in sorted(suite_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                manifest_path = run_dir / "run-manifest.json"
                if not manifest_path.exists():
                    continue
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not isinstance(manifest, dict):
                    continue
                runs.append(run_index_row(manifest, run_dir))
        runs.sort(key=lambda row: int(row["workbench_timestamp_ms"]), reverse=True)
        return templates.TemplateResponse(
            request,
            "index.html",
            {"request": request, "runs": runs, "service_links": service_links()},
        )

    @app.post("/run-smoke")
    def run_smoke() -> RedirectResponse:
        job_id = uuid4().hex
        job_root = workbench_job_root()
        log_path = job_root / f"{job_id}.log"
        exit_path = job_root / f"{job_id}.exit"
        job_root.mkdir(parents=True, exist_ok=True)
        script = self_contained_job_script(log_path, exit_path)
        process = subprocess.Popen(
            ["bash", "-lc", script],
            cwd=Path.cwd(),
        )
        (job_root / f"{job_id}.json").write_text(
            json.dumps(
                {"pid": process.pid, "log_path": str(log_path), "exit_path": str(exit_path)},
                indent=2,
            ),
            encoding="utf-8",
        )
        return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    def job_detail(request: Request, job_id: str) -> HTMLResponse:
        meta = json.loads((workbench_job_root() / f"{job_id}.json").read_text(encoding="utf-8"))
        log_path = Path(meta["log_path"])
        exit_path = Path(meta["exit_path"])
        log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        suite_id, run_id = parse_run_ids(log_text)
        is_complete = exit_path.exists()
        exit_code = int(exit_path.read_text(encoding="utf-8")) if is_complete else None
        progress_steps = job_progress_steps(log_text, is_complete, exit_code)
        can_open_run = bool(
            exit_code == 0 and suite_id and run_id and (runs_root() / suite_id / run_id).exists()
        )
        return templates.TemplateResponse(
            request,
            "job_detail.html",
            {
                "request": request,
                "job_id": job_id,
                "log_text": log_text[-12000:],
                "is_complete": is_complete,
                "exit_code": exit_code,
                "suite_id": suite_id,
                "run_id": run_id,
                "can_open_run": can_open_run,
                "progress_steps": progress_steps,
                "current_step": current_progress_step(progress_steps),
            },
        )

    @app.get("/runs/{suite_id}/{run_id}", response_class=HTMLResponse)
    def run_detail(request: Request, suite_id: str, run_id: str) -> HTMLResponse:
        run_root = runs_root() / suite_id / run_id
        manifest = read_required_run_json(run_root, "run-manifest.json", suite_id, run_id)
        evaluation = read_required_run_json(run_root, "evaluation.json", suite_id, run_id)
        regression = read_required_run_json(run_root, "regression.json", suite_id, run_id)
        tracking = read_required_run_json(run_root, "tracking_export_status.json", suite_id, run_id)
        platforms = {}
        platforms_path = run_root / "review" / "platforms.json"
        if platforms_path.exists():
            platforms = json.loads(platforms_path.read_text(encoding="utf-8"))
        return templates.TemplateResponse(
            request,
            "run_detail.html",
            {
                "request": request,
                "suite_id": suite_id,
                "run_id": run_id,
                "manifest": manifest,
                "evaluation": evaluation,
                "regression": regression,
                "tracking": tracking,
                "platforms": platforms,
                "story": story_summary(run_root),
            },
        )

    @app.get("/generator-package/bundle.json")
    def generator_package_bundle() -> JSONResponse:
        return JSONResponse(generator_package_bundle_payload())

    @app.get("/runs/{suite_id}/{run_id}/story", response_class=HTMLResponse)
    def story_review(request: Request, suite_id: str, run_id: str) -> HTMLResponse:
        run_root = runs_root() / suite_id / run_id
        story = read_required_run_json(run_root, "review/story.json", suite_id, run_id)
        return templates.TemplateResponse(
            request,
            "story.html",
            {
                "request": request,
                "suite_id": suite_id,
                "run_id": run_id,
                "story": story,
            },
        )

    @app.get("/runs/{suite_id}/{run_id}/source-video/{clip_id}/{eye}")
    def source_video(suite_id: str, run_id: str, clip_id: str, eye: str) -> FileResponse:
        run_root = runs_root() / suite_id / run_id
        manifest = read_required_run_json(run_root, "run-manifest.json", suite_id, run_id)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("data_root"), str):
            raise HTTPException(status_code=404, detail=f"Run not found for {suite_id}/{run_id}")
        target = source_video_path(Path(manifest["data_root"]), clip_id, eye)
        if not target.exists() or not target.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"Source video not found for {suite_id}/{run_id}: {clip_id}/{eye}",
            )
        return FileResponse(target, media_type="video/mp4")

    @app.post("/runs/{suite_id}/{run_id}/replay")
    def replay_run(suite_id: str, run_id: str, override: str = Form(...)) -> RedirectResponse:
        child_suite, child_run = LineageReplayService().replay(f"{suite_id}/{run_id}", [override])
        return RedirectResponse(url=f"/runs/{child_suite}/{child_run}", status_code=303)

    @app.post("/runs/{suite_id}/{run_id}/review/open")
    def open_review_platforms_route(suite_id: str, run_id: str) -> RedirectResponse:
        open_review_platforms(suite_id, run_id)
        return RedirectResponse(url=f"/runs/{suite_id}/{run_id}", status_code=303)

    @app.get("/artifacts/{suite_id}/{run_id}/{artifact_path:path}")
    def artifact(suite_id: str, run_id: str, artifact_path: str) -> FileResponse:
        run_root = (runs_root() / suite_id / run_id).resolve()
        target = (run_root / artifact_path).resolve()
        if not target.is_relative_to(run_root):
            raise HTTPException(
                status_code=404,
                detail=f"Artifact not found for {suite_id}/{run_id}: {artifact_path}",
            )
        if not target.exists() or not target.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"Artifact not found for {suite_id}/{run_id}: {artifact_path}",
            )
        return FileResponse(target)

    return app


def read_required_run_json(
    run_root: Path, relative_path: str, suite_id: str, run_id: str
) -> object:
    target = run_root / relative_path
    if not target.exists() or not target.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Run not found for {suite_id}/{run_id}: missing {relative_path}",
        )
    return json.loads(target.read_text(encoding="utf-8"))


def open_review_platforms(suite_id: str, run_id: str) -> None:
    run_root = runs_root() / suite_id / run_id
    manifest = read_required_run_json(run_root, "run-manifest.json", suite_id, run_id)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("config_path"), str):
        raise HTTPException(
            status_code=404,
            detail=f"Run not found for {suite_id}/{run_id}: missing config_path",
        )
    runtime = parse_config_with_runtime_env(Path(manifest["config_path"])).runtime
    ReviewJourneyLauncher().open(
        RunSuiteId(suite_id),
        RunId(run_id),
        runtime,
        run_root,
    )


def source_video_path(data_root: Path, clip_id: str, eye: str) -> Path:
    if eye not in {"left", "right"}:
        raise HTTPException(status_code=404, detail=f"Unsupported source video eye: {eye}")
    root = data_root.resolve()
    file_name = "video_left.mp4" if eye == "left" else "video_right.mp4"
    target = (root / clip_id / file_name).resolve()
    if root not in target.parents:
        raise HTTPException(status_code=404, detail=f"Source video not found: {clip_id}/{eye}")
    return target


def story_summary(run_root: Path) -> dict[str, object]:
    story_path = run_root / "review" / "story.json"
    if not story_path.exists():
        return {"status": "missing", "clip_count": 0}
    story = json.loads(story_path.read_text(encoding="utf-8"))
    clips = story.get("clips", [])
    return {
        "status": "ready",
        "clip_count": len(clips) if isinstance(clips, list) else 0,
        "raw_detection_count": story.get("raw_detection_count", 0),
        "kept_detection_count": story.get("kept_detection_count", 0),
        "rejected_detection_count": story.get("rejected_detection_count", 0),
    }


def run_index_row(manifest: dict[str, object], run_dir: Path) -> dict[str, object]:
    timestamp = manifest_timestamp(manifest, run_dir)
    row = dict(manifest)
    row["workbench_timestamp_iso"] = timestamp.isoformat().replace("+00:00", "Z")
    row["workbench_timestamp_ms"] = int(timestamp.timestamp() * 1000)
    row["workbench_status"] = run_status(run_dir)
    return row


def manifest_timestamp(manifest: dict[str, object], run_dir: Path) -> datetime:
    for key in ("created_at", "started_at", "completed_at", "timestamp", "run_started_at"):
        value = manifest.get(key)
        if isinstance(value, str):
            parsed = parse_datetime(value)
            if parsed is not None:
                return parsed
    for key in ("run_suite_id", "run_id"):
        value = manifest.get(key)
        if isinstance(value, str):
            parsed = parse_timestamp_from_id(value)
            if parsed is not None:
                return parsed
    return datetime.fromtimestamp(run_dir.stat().st_mtime, UTC)


def parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_timestamp_from_id(value: str) -> datetime | None:
    match = re.search(r"(\d{8}T\d{6}(?:\d{6})?Z)", value)
    if not match:
        return None
    raw_timestamp = match.group(1)
    try:
        return datetime.strptime(raw_timestamp, "%Y%m%dT%H%M%S%fZ").replace(tzinfo=UTC)
    except ValueError:
        try:
            return datetime.strptime(raw_timestamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        except ValueError:
            return None


def run_status(run_dir: Path) -> str:
    return "complete" if (run_dir / "review" / "story.json").exists() else "artifacts"


def generator_package_bundle_payload() -> dict[str, object]:
    package_root = Path.cwd() / "generator-package"
    manifest = json.loads(
        (package_root / "generator-package-manifest.json").read_text(encoding="utf-8")
    )
    workspace = json.loads((package_root / "ui" / "workspace.json").read_text(encoding="utf-8"))
    artifacts = [
        generator_package_artifact(
            package_root,
            "schemas/handdetect-run-event.schema.json",
            "application/schema+json",
        ),
        generator_package_artifact(
            package_root,
            "schemas/handdetect-story-row.schema.json",
            "application/schema+json",
        ),
        generator_package_artifact(package_root, "ui/workspace.json", "application/json"),
        generator_package_artifact(
            package_root,
            "ui/themes/handdetect-story.overrides.css",
            "text/css",
        ),
        generator_package_artifact(
            package_root,
            "views/handdetect_story_views.sql",
            "text/sql",
        ),
    ]
    return {
        "artifacts": artifacts,
        "manifest": manifest,
        "workspace": workspace,
    }


def generator_package_artifact(
    package_root: Path, relative_path: str, media_type: str
) -> dict[str, str]:
    return {
        "content": (package_root / relative_path).read_text(encoding="utf-8"),
        "media_type": media_type,
        "path": relative_path,
    }


def serve(host: str, port: int) -> None:
    uvicorn.run(create_app(), host=host, port=port)


def service_links() -> dict[str, str]:
    workbench_url = os.environ.get("HANDDETECT_WORKBENCH_PUBLIC_URL", "").strip()
    biodock_url = os.environ.get("HANDDETECT_BIODOCK_PUBLIC_URL", "").strip()
    mlflow_url = os.environ.get("HANDDETECT_MLFLOW_PUBLIC_URL", "").strip()
    evidently_url = os.environ.get("HANDDETECT_EVIDENTLY_PUBLIC_URL", "").strip()
    fiftyone_url = os.environ.get("HANDDETECT_FIFTYONE_PUBLIC_URL", "").strip()
    label_studio_url = os.environ.get("HANDDETECT_LABEL_STUDIO_PUBLIC_URL", "").strip()
    cvat_url = os.environ.get("HANDDETECT_CVAT_PUBLIC_URL", "").strip()
    rerun_url = os.environ.get("HANDDETECT_RERUN_PUBLIC_URL", "").strip()
    return {
        "workbench": workbench_url or "http://127.0.0.1:8000",
        "biodock": biodock_url or "",
        "mlflow": mlflow_url or "",
        "evidently": evidently_url or "",
        "fiftyone": fiftyone_url or "",
        "label_studio": label_studio_url or "",
        "cvat": cvat_url or "",
        "rerun": rerun_url or "",
    }


def allowed_cors_origins() -> list[str]:
    origins = {
        url.rstrip("/")
        for url in [
            os.environ.get("HANDDETECT_WORKBENCH_PUBLIC_URL", ""),
            os.environ.get("HANDDETECT_BIODOCK_PUBLIC_URL", ""),
            os.environ.get("HANDDETECT_FIFTYONE_PUBLIC_URL", ""),
            os.environ.get("HANDDETECT_LABEL_STUDIO_PUBLIC_URL", ""),
            os.environ.get("HANDDETECT_EVIDENTLY_PUBLIC_URL", ""),
            os.environ.get("HANDDETECT_CVAT_PUBLIC_URL", ""),
            os.environ.get("HANDDETECT_RERUN_PUBLIC_URL", ""),
        ]
        if url.strip()
    }
    return sorted(origins) or ["*"]


def parse_run_ids(log_text: str) -> tuple[str | None, str | None]:
    for line in reversed(log_text.splitlines()):
        match = re.search(r"\bsuite_id=([A-Za-z0-9._:-]+)\s+run_id=([A-Za-z0-9._:-]+)\b", line)
        if match:
            return match.group(1), match.group(2)
    return None, None


def job_progress_steps(
    log_text: str, is_complete: bool, exit_code: int | None
) -> list[dict[str, str]]:
    steps = {
        phase: {
            "phase": phase,
            "label": label,
            "status": "pending",
            "message": "waiting",
        }
        for phase, label in PROGRESS_PHASES
    }
    for line in log_text.splitlines():
        match = PROGRESS_LINE_RE.search(line)
        if not match:
            continue
        phase = match.group("phase")
        if phase not in steps:
            continue
        steps[phase]["status"] = match.group("status")
        steps[phase]["message"] = match.group("message")
    if is_complete and exit_code == 0:
        for step in steps.values():
            if step["status"] == "pending":
                step["status"] = "skipped"
                step["message"] = "not required for this run"
    if is_complete and exit_code not in (None, 0):
        for step in reversed(list(steps.values())):
            if step["status"] == "running":
                step["status"] = "failed"
                step["message"] = step["message"] or "failed"
                break
    return list(steps.values())


def current_progress_step(progress_steps: list[dict[str, str]]) -> dict[str, str] | None:
    for step in progress_steps:
        if step["status"] == "running":
            return step
    for step in progress_steps:
        if step["status"] == "pending":
            return step
    return None


def self_contained_job_script(log_path: Path, exit_path: Path) -> str:
    job_root = workbench_job_root()
    python_executable = sys.executable
    return f"""
set -uo pipefail
mkdir -p {job_root}
status=0
{python_executable} -u -m handdetect.cli.main run-smoke-experiment \\
  --config configs/smoke-experiment.toml 2>&1 | tee {log_path} || status=$?
printf '%s' "$status" > {exit_path}
exit "$status"
""".strip()
