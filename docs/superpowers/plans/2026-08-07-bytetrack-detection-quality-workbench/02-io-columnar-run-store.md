# Task 2: Dataset IO, Columnar Blocks, Run Artifact Store

**Files:**
- Create: `src/handdetect/io/dataset.py`
- Create: `src/handdetect/io/parsers.py`
- Create: `src/handdetect/hotpath/blocks.py`
- Create: `src/handdetect/hotpath/columnar.py`
- Create: `src/handdetect/runs/ids.py`
- Create: `src/handdetect/runs/store.py`
- Create: `src/handdetect/runs/manifest.py`
- Modify: `src/handdetect/cli/main.py`
- Create: `tests/acceptance/test_seed_and_load.py`

**Interfaces:**
- Consumes:
  - `ValidatedClipPathSet`, `ClipId`, `RunId`, `DetectionId`, `FrameIndex`, `TimestampNs`.
  - `RuntimeConfig` from Task 1.
- Produces:
  - `DatasetScanner.scan(data_root: Path) -> tuple[ValidatedClipPathSet, ...]`.
  - `JsonBoundaryParser.parse_clip(paths: ValidatedClipPathSet) -> ValidatedClipBundle`.
  - `ClipColumnBuilder.build(bundle: ValidatedClipBundle) -> DetectionBlock`.
  - `RunArtifactStore.open(runs_root: Path, run_id: RunId) -> RunArtifactStore`.
  - CLI `seed` writes a real seed manifest from downloaded dataset clips.

- [ ] **Step 1: Write failing seed/load acceptance test**

Create `tests/acceptance/test_seed_and_load.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEED_MANIFEST = ROOT / "runs" / "seed" / "seed-manifest.json"


def test_seed_manifest_uses_real_dataset_clips() -> None:
    result = subprocess.run(
        [
            "python",
            "-m",
            "handdetect.cli.main",
            "seed",
            "--data-root",
            "data",
            "--out",
            str(SEED_MANIFEST),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(SEED_MANIFEST.read_text(encoding="utf-8"))
    assert payload["dataset_file_count"] == 235
    assert payload["clip_count"] == 39
    assert "0c54a47b_t010" in payload["smoke_clip_ids"]
```

- [ ] **Step 2: Run the failing acceptance test**

Run:

```bash
python -m pytest tests/acceptance/test_seed_and_load.py -v
```

Expected:

```text
FAILED tests/acceptance/test_seed_and_load.py::test_seed_manifest_uses_real_dataset_clips
```

- [ ] **Step 3: Implement dataset scanner and JSON boundary parser**

Create `src/handdetect/io/dataset.py`:

```python
from __future__ import annotations

from pathlib import Path

from handdetect.domain.ids import ClipId
from handdetect.domain.models import ValidatedClipPathSet


class DatasetScanError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DatasetScanner:
    def scan(self, data_root: Path) -> tuple[ValidatedClipPathSet, ...]:
        if not data_root.exists():
            raise DatasetScanError(f"data root does not exist: {data_root}")
        clips: list[ValidatedClipPathSet] = []
        for clip_dir in sorted(path for path in data_root.iterdir() if path.is_dir()):
            clip_id = ClipId(clip_dir.name)
            paths = ValidatedClipPathSet(
                clip_id=clip_id,
                clip_dir=clip_dir,
                meta_path=clip_dir / "meta.json",
                hand_boxes_path=clip_dir / "hand_boxes.json",
                frame_ts_path=clip_dir / "frame_ts.json",
                vio_pose_path=clip_dir / "vio_pose.json",
                video_left_path=clip_dir / "video_left.mp4",
                video_right_path=clip_dir / "video_right.mp4",
            )
            missing = [path for path in paths.model_dump().values() if isinstance(path, Path) and not path.exists()]
            if missing:
                raise DatasetScanError(f"clip {clip_id} missing required files: {missing}")
            clips.append(paths)
        if not clips:
            raise DatasetScanError(f"data root contains no clip directories: {data_root}")
        return tuple(clips)
```

Create `src/handdetect/io/parsers.py` with the exact public shape:

```python
from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from handdetect.domain.ids import ClipId
from handdetect.domain.models import RawDetection, ValidatedClipPathSet


class ValidatedHandBoxes(BaseModel):
    model_config = ConfigDict(frozen=True)

    detector: str
    eye: str
    video_frame_count: int = Field(gt=0)
    total_detections: int = Field(ge=0)
    frames: tuple[dict[str, object], ...]


class ValidatedFrameTimestamps(BaseModel):
    model_config = ConfigDict(frozen=True)

    cid: ClipId
    fps: float
    frame_count: int = Field(gt=0)
    frame_ts: dict[str, int]


class ValidatedVioPose(BaseModel):
    model_config = ConfigDict(frozen=True)

    t: tuple[float, ...]
    x: tuple[float, ...]
    y: tuple[float, ...]
    z: tuple[float, ...]
    roll: tuple[float, ...]
    pitch: tuple[float, ...]
    yaw: tuple[float, ...]

    @model_validator(mode="after")
    def lengths_match(self) -> "ValidatedVioPose":
        lengths = {len(self.t), len(self.x), len(self.y), len(self.z), len(self.roll), len(self.pitch), len(self.yaw)}
        if len(lengths) != 1:
            raise ValueError("vio pose arrays must have equal lengths")
        return self


class ValidatedClipMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    cid: ClipId
    duration_s: float
    fps: float
    width: int
    height: int


class ValidatedClipBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    paths: ValidatedClipPathSet
    meta: ValidatedClipMeta
    hand_boxes: ValidatedHandBoxes
    frame_ts: ValidatedFrameTimestamps
    vio_pose: ValidatedVioPose


class ClipParseError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class JsonBoundaryParser:
    def parse_clip(self, paths: ValidatedClipPathSet) -> ValidatedClipBundle:
        try:
            meta = ValidatedClipMeta.model_validate(self._read_json(paths.meta_path))
            hand_boxes = ValidatedHandBoxes.model_validate(self._read_json(paths.hand_boxes_path))
            frame_ts = ValidatedFrameTimestamps.model_validate(self._read_json(paths.frame_ts_path))
            vio_pose = ValidatedVioPose.model_validate(self._read_json(paths.vio_pose_path))
        except (OSError, ValidationError, json.JSONDecodeError) as exc:
            raise ClipParseError(f"failed to parse clip {paths.clip_id}: {exc}") from exc
        if meta.cid != paths.clip_id or frame_ts.cid != paths.clip_id:
            raise ClipParseError(f"clip id mismatch for {paths.clip_id}")
        return ValidatedClipBundle(paths=paths, meta=meta, hand_boxes=hand_boxes, frame_ts=frame_ts, vio_pose=vio_pose)

    def _read_json(self, path: Path) -> object:
        return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Implement columnar detection block**

Create `src/handdetect/hotpath/blocks.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
import numpy as np
import numpy.typing as npt

from handdetect.domain.ids import ClipId


Float32Array = npt.NDArray[np.float32]
Int32Array = npt.NDArray[np.int32]
Int64Array = npt.NDArray[np.int64]


class DetectionBlock(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    clip_id: ClipId
    detection_ids: tuple[str, ...]
    frame_index: Int32Array
    xyxy: Float32Array
    confidence: Float32Array
    class_id: Int32Array
    timestamp_ns: Int64Array
```

Create `src/handdetect/hotpath/columnar.py`:

```python
from __future__ import annotations

import numpy as np

from handdetect.hotpath.blocks import DetectionBlock
from handdetect.io.parsers import ValidatedClipBundle


class ClipColumnBuilder:
    def build(self, bundle: ValidatedClipBundle) -> DetectionBlock:
        rows: list[tuple[str, int, float, float, float, float, float, int, int]] = []
        frame_ts = bundle.frame_ts.frame_ts
        for frame_payload in bundle.hand_boxes.frames:
            frame = int(frame_payload["frame"])
            detections = frame_payload.get("detections", [])
            if not isinstance(detections, list):
                raise ValueError(f"invalid detections list in clip {bundle.paths.clip_id} frame {frame}")
            for ordinal, detection in enumerate(detections):
                if not isinstance(detection, dict):
                    raise ValueError(f"invalid detection object in clip {bundle.paths.clip_id} frame {frame}")
                xyxy = detection["xyxy"]
                if not isinstance(xyxy, list) or len(xyxy) != 4:
                    raise ValueError(f"invalid xyxy in clip {bundle.paths.clip_id} frame {frame}")
                detection_id = f"{bundle.paths.clip_id}:{frame}:{ordinal}"
                rows.append(
                    (
                        detection_id,
                        frame,
                        float(xyxy[0]),
                        float(xyxy[1]),
                        float(xyxy[2]),
                        float(xyxy[3]),
                        float(detection["confidence"]),
                        int(detection["class"]),
                        int(frame_ts[str(frame)]),
                    )
                )
        xyxy_array = np.asarray([row[2:6] for row in rows], dtype=np.float32)
        return DetectionBlock(
            clip_id=bundle.paths.clip_id,
            detection_ids=tuple(row[0] for row in rows),
            frame_index=np.asarray([row[1] for row in rows], dtype=np.int32),
            xyxy=xyxy_array,
            confidence=np.asarray([row[6] for row in rows], dtype=np.float32),
            class_id=np.asarray([row[7] for row in rows], dtype=np.int32),
            timestamp_ns=np.asarray([row[8] for row in rows], dtype=np.int64),
        )
```

- [ ] **Step 5: Implement run ids, manifests, and store**

Create `src/handdetect/runs/ids.py`:

```python
from __future__ import annotations

import hashlib

from handdetect.domain.ids import ExperimentId, RunId


class DeterministicRunIdProvider:
    def create(self, experiment_id: ExperimentId, config_bytes: bytes) -> RunId:
        digest = hashlib.sha256(config_bytes).hexdigest()[:16]
        return RunId(f"{experiment_id}-{digest}")
```

Create `src/handdetect/runs/manifest.py`:

```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from handdetect.domain.ids import ClipId, ExperimentId, RunId


class SeedManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_root: Path
    dataset_file_count: int
    clip_count: int
    smoke_clip_ids: tuple[ClipId, ...]


class RunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: RunId
    experiment_id: ExperimentId
    data_root: Path
    output_root: Path
    clip_ids: tuple[ClipId, ...]
    config_sha256: str
```

Create `src/handdetect/runs/store.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from handdetect.domain.ids import RunId
from handdetect.runs.manifest import SeedManifest


class RunArtifactStore:
    def __init__(self, runs_root: Path, run_id: RunId) -> None:
        self.runs_root = runs_root
        self.run_id = run_id
        self.root = runs_root / str(run_id)
        self.audit_dir = self.root / "audit"
        self.cleaned_dir = self.root / "cleaned"
        self.tables_dir = self.root / "tables"
        self.report_dir = self.root / "report"

    @classmethod
    def open(cls, runs_root: Path, run_id: RunId) -> "RunArtifactStore":
        store = cls(runs_root, run_id)
        for path in [store.audit_dir, store.cleaned_dir, store.tables_dir, store.report_dir]:
            path.mkdir(parents=True, exist_ok=True)
        return store


class SeedManifestWriter:
    def write(self, manifest: SeedManifest, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        temp_path.replace(path)
```

- [ ] **Step 6: Wire CLI seed to scanner**

Modify `src/handdetect/cli/main.py` top-level imports:

```python
from handdetect.io.dataset import DatasetScanner
from handdetect.runs.manifest import SeedManifest
from handdetect.runs.store import SeedManifestWriter
```

Modify `src/handdetect/cli/main.py` `seed()` command body:

```python
@app.command()
def seed(data_root: Path, out: Path) -> None:
    scanner = DatasetScanner()
    clips = scanner.scan(data_root)
    file_count = sum(1 for path in data_root.rglob("*") if path.is_file())
    smoke_ids = tuple(clip.clip_id for clip in clips[:3])
    manifest = SeedManifest(
        dataset_root=data_root,
        dataset_file_count=file_count,
        clip_count=len(clips),
        smoke_clip_ids=smoke_ids,
    )
    SeedManifestWriter().write(manifest, out)
    typer.echo(f"handdetect seed: wrote {out} with {len(clips)} clips")
```

- [ ] **Step 7: Run acceptance test and commit**

Run:

```bash
python -m pytest tests/acceptance/test_seed_and_load.py -v
make check
```

Expected:

```text
1 passed
```

Commit:

```bash
git add src/handdetect/io src/handdetect/hotpath src/handdetect/runs src/handdetect/cli/main.py tests/acceptance/test_seed_and_load.py
git commit -m "feat: add dataset scanner and run store"
```
