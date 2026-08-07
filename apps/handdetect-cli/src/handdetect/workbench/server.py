from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from handdetect.lineage.replay import LineageReplayService
from handdetect.runtime_paths import runs_root, workbench_job_root


def create_app() -> FastAPI:
    app = FastAPI(title="HandDetect Workbench")
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        runs = []
        current_runs_root = runs_root()
        for suite_dir in sorted(current_runs_root.glob("suite-*")):
            for run_dir in sorted(suite_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                manifest_path = run_dir / "run-manifest.json"
                if not manifest_path.exists():
                    continue
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                runs.append(manifest)
        return templates.TemplateResponse(request, "index.html", {"request": request, "runs": runs})

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
            },
        )

    @app.post("/runs/{suite_id}/{run_id}/replay")
    def replay_run(suite_id: str, run_id: str, override: str = Form(...)) -> RedirectResponse:
        child_suite, child_run = LineageReplayService().replay(f"{suite_id}/{run_id}", [override])
        return RedirectResponse(url=f"/runs/{child_suite}/{child_run}", status_code=303)

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


def serve(host: str, port: int) -> None:
    uvicorn.run(create_app(), host=host, port=port)


def parse_run_ids(log_text: str) -> tuple[str | None, str | None]:
    for line in reversed(log_text.splitlines()):
        match = re.search(r"\bsuite_id=([A-Za-z0-9._:-]+)\s+run_id=([A-Za-z0-9._:-]+)\b", line)
        if match:
            return match.group(1), match.group(2)
    return None, None


def self_contained_job_script(log_path: Path, exit_path: Path) -> str:
    job_root = workbench_job_root()
    return f"""
set -uo pipefail
mkdir -p {job_root}
status=0
python -m handdetect.cli.main run \\
  --config configs/smoke-experiment.toml 2>&1 | tee {log_path} || status=$?
if [ "$status" -eq 0 ]; then
  suite_id=$(sed -n 's/.*suite_id=\\([^ ]*\\).*/\\1/p' {log_path} | tail -1)
  run_id=$(sed -n 's/.*run_id=\\([^ ]*\\).*/\\1/p' {log_path} | tail -1)
  if [ -n "$suite_id" ] && [ -n "$run_id" ]; then
    python -m handdetect.cli.main review open \\
      --suite-id "$suite_id" \\
      --run-id "$run_id" >> {log_path} 2>&1 || status=$?
  else
    status=1
  fi
fi
printf '%s' "$status" > {exit_path}
exit "$status"
""".strip()
