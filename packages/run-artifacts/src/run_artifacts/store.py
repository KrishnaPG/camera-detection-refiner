from __future__ import annotations

import json
from pathlib import Path

from dq_contracts.ids import RunId, RunSuiteId

from run_artifacts.manifest import SeedManifest


class RunArtifactStore:
    def __init__(self, runs_root: Path, suite_id: RunSuiteId, run_id: RunId) -> None:
        self.runs_root = runs_root
        self.suite_id = suite_id
        self.run_id = run_id
        self.root = runs_root / str(suite_id) / str(run_id)
        self.audit_dir = self.root / "audit"
        self.cleaned_dir = self.root / "cleaned"
        self.tables_dir = self.root / "tables"
        self.report_dir = self.root / "report"
        self.review_dir = self.root / "review"
        self.lineage_dir = self.root / "lineage"

    @classmethod
    def open(cls, runs_root: Path, suite_id: RunSuiteId, run_id: RunId) -> RunArtifactStore:
        store = cls(runs_root, suite_id, run_id)
        if store.root.exists():
            raise FileExistsError(
                f"run root already exists and will not be overwritten: {store.root}"
            )
        for path in (
            store.audit_dir,
            store.cleaned_dir,
            store.tables_dir,
            store.report_dir,
            store.review_dir,
            store.lineage_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return store


class SeedManifestWriter:
    def write(self, manifest: SeedManifest, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        temp_path.replace(path)

    def write_json(self, value: dict, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")
