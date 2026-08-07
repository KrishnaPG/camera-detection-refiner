from __future__ import annotations

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from handdetect.runs.manifest import RunIndexRow


class RunCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.index_dir = root / "index"
        self.run_index_path = self.index_dir / "run_index.parquet"
        self.metric_history_path = self.index_dir / "metric_history.parquet"

    @classmethod
    def open(cls, runs_root: Path) -> RunCatalog:
        catalog = cls(runs_root)
        catalog.index_dir.mkdir(parents=True, exist_ok=True)
        return catalog

    def append_run(self, manifest: RunIndexRow) -> None:
        with self._locked():
            row = pa.table(
                {key: [value] for key, value in manifest.model_dump(mode="json").items()}
            )
            if self.run_index_path.exists():
                existing = pq.read_table(self.run_index_path)
                row = pa.concat_tables([existing, row], promote_options="default")
            temp_path = self.run_index_path.with_suffix(".tmp")
            pq.write_table(row, temp_path)
            temp_path.replace(self.run_index_path)

    def append_metrics(self, rows: list[dict[str, object]]) -> None:
        if not rows:
            return
        with self._locked():
            table = pa.table({key: [row[key] for row in rows] for key in rows[0].keys()})
            if self.metric_history_path.exists():
                existing = pq.read_table(self.metric_history_path)
                table = pa.concat_tables([existing, table], promote_options="default")
            temp_path = self.metric_history_path.with_suffix(".tmp")
            pq.write_table(table, temp_path)
            temp_path.replace(self.metric_history_path)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        lock_path = self.index_dir / "catalog.lock"
        with lock_path.open("w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
