from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import tomlkit
from dq_boundaries.config import ExperimentConfigParser
from dq_contracts.ids import RunId, RunSuiteId
from handdetect.review_journey.launcher import ReviewJourneyLauncher
from handdetect.runtime_paths import dvclive_root, mlflow_root, replay_root


class LineageReplayService:
    def replay(self, from_run: str, overrides: list[str]) -> tuple[str, str]:
        suite_id, run_id = from_run.split("/", 1)
        parent_root = Path("runs") / suite_id / run_id
        parent_lock = json.loads(
            (parent_root / "lineage" / "replay.lock.json").read_text(encoding="utf-8")
        )
        parent_manifest = json.loads(
            (parent_root / "run-manifest.json").read_text(encoding="utf-8")
        )
        current_replay_root = replay_root() / self._replay_id()
        worktree = current_replay_root / "worktree"
        worktree.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree), parent_lock["git"]["commit_sha"]],
            check=True,
            text=True,
        )
        dirty_patch = parent_root / "lineage" / "dirty.patch"
        if dirty_patch.exists():
            subprocess.run(
                ["git", "apply", str(dirty_patch.resolve())],
                cwd=worktree,
                check=True,
                text=True,
            )
        self._restore_source_snapshot(parent_root / "lineage" / "source-snapshot", worktree)
        config_path = (worktree / "configs" / f"replay-{suite_id}-{run_id}.toml").resolve()
        self._write_override_config(Path(parent_manifest["config_path"]), config_path, overrides)
        status_path = current_replay_root / "replay-status.jsonl"
        status_path.write_text('{"status":"starting"}\n', encoding="utf-8")
        result = subprocess.run(
            ["python", "-m", "handdetect.cli.main", "run", "--config", str(config_path)],
            cwd=worktree,
            text=True,
            capture_output=True,
            check=True,
        )
        child_suite = result.stdout.split("suite_id=", 1)[1].split()[0]
        child_run = result.stdout.split("run_id=", 1)[1].split()[0]
        status_path.write_text(
            json.dumps(
                {"status": "complete", "child_suite_id": child_suite, "child_run_id": child_run},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        child_lock_path = Path("runs") / child_suite / child_run / "lineage" / "replay.lock.json"
        child_lock = json.loads(child_lock_path.read_text(encoding="utf-8"))
        child_lock["parent"] = {"run_suite_id": suite_id, "run_id": run_id}
        child_lock_path.write_text(json.dumps(child_lock, indent=2), encoding="utf-8")
        self._publish_child_review(child_suite, child_run, config_path)
        return child_suite, child_run

    def cleanup(self) -> None:
        current_replay_root = replay_root()
        if current_replay_root.exists():
            shutil.rmtree(current_replay_root)

    def _replay_id(self) -> str:
        return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")

    def _write_override_config(self, source: Path, target: Path, overrides: list[str]) -> None:
        document = tomlkit.parse(source.read_text(encoding="utf-8"))
        target.parent.mkdir(parents=True, exist_ok=True)
        runtime = document["runtime"]
        runtime["data_root"] = str(Path.cwd() / "data")
        runtime["runs_root"] = str(Path.cwd() / "runs")
        runtime["dvclive_root"] = str(dvclive_root())
        runtime["mlflow_tracking_uri"] = str(mlflow_root())
        runtime["evidently_root"] = str(Path.cwd() / "runs" / "evidently")
        for item in overrides:
            key, value = item.split("=", 1)
            section_name, field_name = key.split(".", 1)
            document["experiments"][0][section_name][field_name] = tomlkit.float_(float(value))
        target.write_text(tomlkit.dumps(document), encoding="utf-8")

    def _restore_source_snapshot(self, snapshot_root: Path, worktree: Path) -> None:
        if not snapshot_root.exists():
            return
        for item in snapshot_root.iterdir():
            target = worktree / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)

    def _publish_child_review(self, child_suite: str, child_run: str, config_path: Path) -> None:
        runtime = ExperimentConfigParser().parse_path(config_path).runtime
        child_root = runtime.runs_root / child_suite / child_run
        ReviewJourneyLauncher().open(RunSuiteId(child_suite), RunId(child_run), runtime, child_root)
