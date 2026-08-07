from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class GitLineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    commit_sha: str
    dependency_lock_sha256: str
    dirty_patch_sha256: str | None = None


class ArtifactLineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    logical_name: str
    path: Path
    content_sha256: str
    dvc_hash: str | None = None


class TrackingLineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    mlflow_run_id: str | None
    tracking_uri: str


class ParentRunRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_suite_id: str
    run_id: str


class ReplayLock(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_suite_id: str
    run_id: str
    restore_authority: str = "content_snapshot"
    git: GitLineageRef
    dataset: ArtifactLineageRef
    labels: ArtifactLineageRef
    config: ArtifactLineageRef
    tracking: TrackingLineageRef
    parent: ParentRunRef | None = None
