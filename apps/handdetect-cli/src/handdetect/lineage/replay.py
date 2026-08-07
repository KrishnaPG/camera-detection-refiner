from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import tomlkit
from dq_boundaries.config import ExperimentConfigParser
from dq_contracts.ids import RunId, RunSuiteId
from handdetect.review_journey.launcher import ReviewJourneyLauncher
from handdetect.runtime_paths import dvclive_root, mlflow_root, replay_root, runs_root


class LineageReplayService:
    def replay(self, from_run: str, overrides: list[str]) -> tuple[str, str]:
        suite_id, run_id = from_run.split("/", 1)
        main_root = Path.cwd()
        main_runs_root = runs_root()
        parent_root = main_runs_root / suite_id / run_id
        parent_lock = json.loads(
            (parent_root / "lineage" / "replay.lock.json").read_text(encoding="utf-8")
        )
        current_replay_root = replay_root() / self._replay_id()
        worktree = current_replay_root / "worktree"
        worktree.parent.mkdir(parents=True, exist_ok=True)
        snapshot_root = parent_root / "lineage" / "source-snapshot"
        restore_mode = self._restore_source_snapshot(snapshot_root, worktree)
        if restore_mode != "source_snapshot":
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "--detach",
                    str(worktree),
                    parent_lock["git"]["commit_sha"],
                ],
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
        status_path = current_replay_root / "replay-status.jsonl"
        self._append_status(status_path, {"status": "starting"})
        restore = self._restore_inputs(parent_lock, worktree, main_root)
        restore["source_mode"] = restore_mode
        config_path = (worktree / "configs" / f"replay-{suite_id}-{run_id}.toml").resolve()
        self._write_override_config(parent_lock, config_path, overrides, worktree, main_root)
        result = subprocess.run(
            ["python", "-m", "handdetect.cli.main", "run", "--config", str(config_path)],
            cwd=worktree,
            text=True,
            capture_output=True,
            check=True,
        )
        child_suite = result.stdout.split("suite_id=", 1)[1].split()[0]
        child_run = result.stdout.split("run_id=", 1)[1].split()[0]
        self._append_status(
            status_path,
            {
                "status": "complete",
                "restore": restore,
                "child_suite_id": child_suite,
                "child_run_id": child_run,
            },
        )
        child_lock_path = main_runs_root / child_suite / child_run / "lineage" / "replay.lock.json"
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

    def _write_override_config(
        self,
        parent_lock: dict[str, object],
        target: Path,
        overrides: list[str],
        worktree: Path,
        main_root: Path,
    ) -> None:
        source = self._worktree_input_path(worktree, str(parent_lock["config"]["path"]))
        document = tomlkit.parse(source.read_text(encoding="utf-8"))
        target.parent.mkdir(parents=True, exist_ok=True)
        runtime = document["runtime"]
        runtime["data_root"] = str(
            self._worktree_input_path(worktree, str(parent_lock["dataset"]["path"]))
        )
        runtime["runs_root"] = str(runs_root())
        runtime["dvclive_root"] = str(dvclive_root())
        runtime["mlflow_tracking_uri"] = str(mlflow_root())
        runtime["evidently_root"] = str(runs_root() / "evidently")
        for item in overrides:
            key, value = item.split("=", 1)
            section_name, field_name = key.split(".", 1)
            document["experiments"][0][section_name][field_name] = tomlkit.float_(float(value))
        target.write_text(tomlkit.dumps(document), encoding="utf-8")

    def _restore_source_snapshot(self, snapshot_root: Path, worktree: Path) -> str:
        if not snapshot_root.exists():
            return "git_worktree"
        worktree.mkdir(parents=True, exist_ok=True)
        for item in snapshot_root.iterdir():
            target = worktree / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
        return "source_snapshot"

    def _restore_inputs(
        self,
        parent_lock: dict[str, object],
        worktree: Path,
        main_root: Path,
    ) -> dict[str, object]:
        if self._has_dvc_metadata(worktree):
            for command in (["dvc", "pull"], ["dvc", "checkout"]):
                subprocess.run(command, cwd=worktree, check=True, text=True)
            return {"mode": "dvc", "used_dvc": True}
        restored_from_content_refs = []
        for key in ("dataset", "labels", "config"):
            path_value = str(parent_lock[key]["path"])
            if self._ensure_worktree_input(main_root, worktree, path_value):
                restored_from_content_refs.append(path_value)
        return {
            "mode": "source_snapshot",
            "used_dvc": False,
            "dataset_path": str(parent_lock["dataset"]["path"]),
            "label_path": str(parent_lock["labels"]["path"]),
            "config_path": str(parent_lock["config"]["path"]),
            "restored_from_content_refs": restored_from_content_refs,
        }

    def _has_dvc_metadata(self, worktree: Path) -> bool:
        if (worktree / "dvc.yaml").exists() or (worktree / "dvc.lock").exists():
            return True
        return any(worktree.rglob("*.dvc"))

    def _worktree_input_path(self, worktree: Path, path_value: str) -> Path:
        lineage_path = Path(path_value)
        if lineage_path.is_absolute():
            return lineage_path
        return (worktree / lineage_path).resolve()

    def _ensure_worktree_input(self, main_root: Path, worktree: Path, path_value: str) -> bool:
        target = self._worktree_input_path(worktree, path_value)
        if target.exists():
            return False
        lineage_path = Path(path_value)
        source = (
            lineage_path if lineage_path.is_absolute() else (main_root / lineage_path).resolve()
        )
        if not source.exists():
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            os.symlink(source, target, target_is_directory=True)
        else:
            os.symlink(source, target)
        return True

    def _append_status(self, status_path: Path, payload: dict[str, object]) -> None:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        with status_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _publish_child_review(self, child_suite: str, child_run: str, config_path: Path) -> None:
        runtime = ExperimentConfigParser().parse_path(config_path).runtime
        child_root = runtime.runs_root / child_suite / child_run
        ReviewJourneyLauncher().open(RunSuiteId(child_suite), RunId(child_run), runtime, child_root)
