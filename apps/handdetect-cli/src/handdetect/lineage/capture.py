from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from dq_contracts.ids import RunId, RunSuiteId
from handdetect.lineage.models import (
    ArtifactLineageRef,
    GitLineageRef,
    ParentRunRef,
    ReplayLock,
    TrackingLineageRef,
)


class LineageSnapshotWriter:
    def write(
        self,
        run_root: Path,
        suite_id: RunSuiteId,
        run_id: RunId,
        config_path: Path,
        data_root: Path,
        label_set_path: Path,
        parent: ParentRunRef | None = None,
    ) -> Path:
        tracking = json.loads(
            (run_root / "tracking_export_status.json").read_text(encoding="utf-8")
        )
        lock = ReplayLock(
            run_suite_id=str(suite_id),
            run_id=str(run_id),
            git=GitLineageRef(
                commit_sha=self._git_commit(),
                dependency_lock_sha256=self._file_hash(Path("pyproject.toml")),
                dirty_patch_sha256=self._write_dirty_patch(run_root / "lineage" / "dirty.patch"),
            ),
            dataset=ArtifactLineageRef(
                logical_name="dataset",
                path=data_root,
                content_sha256=self._tree_hash(data_root),
            ),
            labels=ArtifactLineageRef(
                logical_name="labels",
                path=label_set_path,
                content_sha256=self._tree_hash(label_set_path),
            ),
            config=ArtifactLineageRef(
                logical_name="config",
                path=config_path,
                content_sha256=self._file_hash(config_path),
            ),
            tracking=TrackingLineageRef(
                mlflow_run_id=tracking["mlflow"].get("run_id"),
                tracking_uri=tracking["mlflow"]["path"],
            ),
            parent=parent,
        )
        output = run_root / "lineage" / "replay.lock.json"
        self._write_source_snapshot(run_root / "lineage" / "source-snapshot")
        output.write_text(lock.model_dump_json(indent=2), encoding="utf-8")
        return output

    def _git_commit(self) -> str:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()

    def _write_dirty_patch(self, output: Path) -> str | None:
        patch = subprocess.check_output(["git", "diff", "HEAD"], text=True)
        if not patch.strip():
            return None
        output.write_text(patch, encoding="utf-8")
        return hashlib.sha256(patch.encode("utf-8")).hexdigest()

    def _file_hash(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _tree_hash(self, root: Path) -> str:
        hasher = hashlib.sha256()
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            hasher.update(str(path.relative_to(root)).encode("utf-8"))
            hasher.update(path.read_bytes())
        return hasher.hexdigest()

    def _write_source_snapshot(self, snapshot_root: Path) -> None:
        snapshot_root.mkdir(parents=True, exist_ok=True)
        for name in ["apps", "packages", "handdetect", "configs", "labels"]:
            source = Path(name)
            target = snapshot_root / name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        for name in ["pyproject.toml", "Makefile", "README.md"]:
            shutil.copy2(Path(name), snapshot_root / name)
