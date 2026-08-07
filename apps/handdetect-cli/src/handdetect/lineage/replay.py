from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import tomlkit
from dq_boundaries.config import ExperimentConfigParser
from dq_contracts.ids import RunId, RunSuiteId
from handdetect.regression.gates import RegressionGateRunner
from handdetect.report.static_report import StaticReportBuilder
from handdetect.review_journey.launcher import ReviewJourneyLauncher
from handdetect.runtime_paths import dvclive_root, mlflow_root, replay_root, runs_root


class LineageReplayService:
    def replay(self, from_run: str, overrides: list[str]) -> tuple[str, str]:
        suite_id, run_id = from_run.split("/", 1)
        main_root = Path.cwd()
        main_runs_root = runs_root()
        parent_root = main_runs_root / suite_id / run_id
        parent_manifest = json.loads(
            (parent_root / "run-manifest.json").read_text(encoding="utf-8")
        )
        parent_experiment_id = self._parent_experiment_id(parent_manifest, run_id)
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
        self._write_override_config(
            parent_lock,
            parent_experiment_id,
            config_path,
            overrides,
            worktree,
        )
        result = subprocess.run(
            ["python", "-m", "handdetect.cli.main", "run", "--config", str(config_path)],
            cwd=worktree,
            text=True,
            capture_output=True,
            check=True,
        )
        child_suite, child_run = self._select_child_run(
            result.stdout,
            main_runs_root,
            parent_experiment_id,
        )
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
        child_lock["restore_authority"] = "content_snapshot"
        child_lock_path.write_text(json.dumps(child_lock, indent=2), encoding="utf-8")
        child_root = main_runs_root / child_suite / child_run
        RegressionGateRunner().check(child_root, parent_root)
        self._write_parent_comparison(child_root, parent_root)
        StaticReportBuilder().build(child_root)
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
        experiment_id: str,
        target: Path,
        overrides: list[str],
        worktree: Path,
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
        self._apply_review_runtime_env_overrides(runtime)
        experiment = self._target_experiment(document, experiment_id)
        for item in overrides:
            self._apply_override(document, experiment, item)
        target.write_text(tomlkit.dumps(document), encoding="utf-8")
        ExperimentConfigParser().parse_path(target)

    def _apply_review_runtime_env_overrides(self, runtime: tomlkit.items.Table) -> None:
        env_map = {
            "HANDDETECT_LABEL_STUDIO_URL": "label_studio_url",
            "HANDDETECT_LABEL_STUDIO_PUBLIC_URL": "label_studio_public_url",
            "HANDDETECT_LABEL_STUDIO_TOKEN": "label_studio_token",
        }
        for env_name, field_name in env_map.items():
            value = os.environ.get(env_name, "").strip()
            if value:
                runtime[field_name] = value

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
            self._verify_restored_inputs(parent_lock, worktree)
            return {
                "mode": "content_snapshot",
                "restore_authority": "content_snapshot",
                "used_dvc_checkout": True,
            }
        restored_from_content_refs = []
        for key in ("dataset", "labels", "config"):
            path_value = str(parent_lock[key]["path"])
            if self._ensure_worktree_input(main_root, worktree, path_value):
                restored_from_content_refs.append(path_value)
            target = self._worktree_input_path(worktree, path_value)
            if not target.exists():
                raise RuntimeError(f"replay {key} missing at recorded path {target}")
            self._verify_content_ref(parent_lock, key, target)
        return {
            "mode": "content_snapshot",
            "restore_authority": "content_snapshot",
            "used_dvc_checkout": False,
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

    def _verify_restored_inputs(self, parent_lock: dict[str, object], worktree: Path) -> None:
        for key in ("dataset", "labels", "config"):
            path_value = str(parent_lock[key]["path"])
            target = self._worktree_input_path(worktree, path_value)
            if not target.exists():
                raise RuntimeError(f"replay {key} missing at recorded path {target}")
            self._verify_content_ref(parent_lock, key, target)

    def _verify_content_ref(self, parent_lock: dict[str, object], key: str, path: Path) -> None:
        expected = str(parent_lock[key]["content_sha256"])
        actual = self._tree_hash(path) if path.is_dir() else self._file_hash(path)
        if actual != expected:
            raise RuntimeError(
                f"replay {key} content drift: expected sha256 {expected}, got {actual} at {path}"
            )

    def _file_hash(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _tree_hash(self, root: Path) -> str:
        hasher = hashlib.sha256()
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            hasher.update(str(path.relative_to(root)).encode("utf-8"))
            hasher.update(path.read_bytes())
        return hasher.hexdigest()

    def _append_status(self, status_path: Path, payload: dict[str, object]) -> None:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        with status_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _apply_override(
        self,
        document: tomlkit.TOMLDocument,
        experiment: tomlkit.items.Table,
        item: str,
    ) -> None:
        key, raw_value = item.split("=", 1)
        parsed_value = tomlkit.parse(f"value = {raw_value}\n")["value"]
        if key.startswith("runtime."):
            _, field_name = key.split(".", 1)
            document["runtime"][field_name] = parsed_value
            return
        if "." not in key:
            experiment[key] = parsed_value
            return
        section_name, field_name = key.split(".", 1)
        experiment[section_name][field_name] = parsed_value

    def _target_experiment(
        self,
        document: tomlkit.TOMLDocument,
        experiment_id: str,
    ) -> tomlkit.items.Table:
        for experiment in document["experiments"]:
            if str(experiment["name"]) == experiment_id:
                return experiment
        raise RuntimeError(f"replay experiment {experiment_id} not found in config")

    def _parent_experiment_id(self, parent_manifest: dict[str, object], run_id: str) -> str:
        experiment_id = parent_manifest.get("experiment_id")
        if isinstance(experiment_id, str) and experiment_id:
            return experiment_id
        return run_id.split("-", 1)[0]

    def _select_child_run(
        self,
        stdout: str,
        main_runs_root: Path,
        experiment_id: str,
    ) -> tuple[str, str]:
        candidates = self._parse_run_output(stdout)
        if not candidates:
            raise RuntimeError(f"replay could not find child run in output: {stdout!r}")
        for suite_id, run_id in candidates:
            manifest_path = main_runs_root / suite_id / run_id / "run-manifest.json"
            if not manifest_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("experiment_id") == experiment_id:
                return suite_id, run_id
        for suite_id, run_id in candidates:
            if run_id == experiment_id or run_id.startswith(f"{experiment_id}-"):
                return suite_id, run_id
        return candidates[0]

    def _parse_run_output(self, stdout: str) -> list[tuple[str, str]]:
        pattern = re.compile(r"\bsuite_id=([A-Za-z0-9._:-]+)\s+run_id=([A-Za-z0-9._:-]+)\b")
        results: list[tuple[str, str]] = []
        for line in stdout.splitlines():
            match = pattern.search(line)
            if match:
                results.append((match.group(1), match.group(2)))
        return results

    def _publish_child_review(self, child_suite: str, child_run: str, config_path: Path) -> None:
        runtime = ExperimentConfigParser().parse_path(config_path).runtime
        child_root = runtime.runs_root / child_suite / child_run
        ReviewJourneyLauncher().open(RunSuiteId(child_suite), RunId(child_run), runtime, child_root)

    def _write_parent_comparison(self, child_root: Path, parent_root: Path) -> None:
        child_eval = json.loads((child_root / "evaluation.json").read_text(encoding="utf-8"))
        parent_eval = json.loads((parent_root / "evaluation.json").read_text(encoding="utf-8"))
        metrics = ["raw_detection_count", "cleaned_detection_count", "rejected_detection_count"]
        comparison = {
            "parent_run_root": str(parent_root),
            "metric_deltas": {
                metric: child_eval.get(metric, 0) - parent_eval.get(metric, 0) for metric in metrics
            },
        }
        output = child_root / "lineage" / "parent-comparison.json"
        output.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
