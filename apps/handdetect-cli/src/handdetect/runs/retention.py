from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from handdetect.runtime_paths import runtime_state_root

DEFAULT_MAX_BYTES = 20 * 1024 * 1024 * 1024
DEFAULT_MIN_FREE_BYTES = 5 * 1024 * 1024 * 1024
DEFAULT_KEEP_SUITES = 5


@dataclass(frozen=True)
class RetentionResult:
    root: Path
    bytes_before: int
    bytes_after: int
    removed_paths: tuple[Path, ...]


class RuntimeRetentionPruner:
    def __init__(
        self,
        *,
        max_bytes: int | None = None,
        min_free_bytes: int | None = None,
        keep_suites: int | None = None,
    ) -> None:
        self.max_bytes = (
            max_bytes
            if max_bytes is not None
            else _env_int(
                "HANDDETECT_MAX_RUNTIME_BYTES",
                DEFAULT_MAX_BYTES,
            )
        )
        self.min_free_bytes = (
            min_free_bytes
            if min_free_bytes is not None
            else _env_int(
                "HANDDETECT_MIN_FREE_BYTES",
                DEFAULT_MIN_FREE_BYTES,
            )
        )
        self.keep_suites = (
            keep_suites
            if keep_suites is not None
            else _env_int(
                "HANDDETECT_KEEP_SUITES",
                DEFAULT_KEEP_SUITES,
            )
        )

    def prune(self, root: Path, *, protect: tuple[Path, ...] = ()) -> RetentionResult:
        _ensure_directory(root)
        bytes_before = _directory_size(root)
        current_bytes = bytes_before
        removed: list[Path] = []
        protected = {path.resolve() for path in protect if path.exists()}
        protected_in_root = {path for path in protected if path.is_relative_to(root.resolve())}
        candidates = self._candidates(root, protected)
        candidate_count = len(candidates) + len(protected_in_root)

        while candidates and self._must_prune(root, current_bytes, candidate_count):
            target = candidates.pop(0)
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            removed.append(target)
            current_bytes = _directory_size(root)
            candidate_count -= 1

        return RetentionResult(
            root=root,
            bytes_before=bytes_before,
            bytes_after=current_bytes,
            removed_paths=tuple(removed),
        )

    def _must_prune(self, root: Path, current_bytes: int, suite_count: int) -> bool:
        free_bytes = shutil.disk_usage(root).free
        return (
            current_bytes > self.max_bytes
            or free_bytes < self.min_free_bytes
            or suite_count > self.keep_suites
        )

    def prune_default_runtime(
        self, *, protect: tuple[Path, ...] = ()
    ) -> tuple[RetentionResult, ...]:
        runtime_root = runtime_state_root()
        _ensure_directory(runtime_root)
        roots = (
            runtime_root / "runs",
            runtime_root / "dvclive",
            runtime_root / "evidently",
            runtime_root / "replays",
            runtime_root / "workbench" / "jobs",
            runtime_root / "cache",
        )
        return tuple(self.prune(root, protect=protect) for root in roots if root.exists())

    def _candidates(self, root: Path, protected: set[Path]) -> list[Path]:
        suites = [path for path in root.glob("suite-*") if path.is_dir()]
        possible = suites if suites else [path for path in root.iterdir()]
        candidates = [path for path in possible if path.resolve() not in protected]
        return sorted(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def _ensure_directory(path: Path) -> None:
    if path.is_symlink():
        resolved = path.resolve(strict=False)
        if not path.exists() or not str(resolved).startswith("/tmp/"):
            path.unlink()
    path.mkdir(parents=True, exist_ok=True)
