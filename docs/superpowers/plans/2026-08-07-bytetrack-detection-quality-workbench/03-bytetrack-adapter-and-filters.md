# Task 3: ByteTrack Adapter, False-Positive Filters, Selector, Audit Decisions

**Files:**
- Create: `src/handdetect/filters/results.py`
- Create: `src/handdetect/filters/registry.py`
- Create: `src/handdetect/filters/geometric.py`
- Create: `src/handdetect/tracking/interfaces.py`
- Create: `src/handdetect/tracking/bytetrack.py`
- Create: `src/handdetect/filters/temporal.py`
- Create: `src/handdetect/selection/max_two.py`
- Create: `src/handdetect/audit/ledger.py`
- Create: `tests/acceptance/test_adapter_smoke.py`

**Interfaces:**
- Consumes:
  - `DetectionBlock` from Task 2.
  - `AdapterConfig` and `ByteTrackConfig` from Task 1.
- Produces:
  - `GeometricStageResult`, `TrackBlock`, `TemporalStageResult`, `SelectedDetectionBlock`.
  - `ByteTrackAssociationAdapter.associate(block: DetectionBlock, config: ByteTrackConfig) -> TrackBlock`.
  - `DecisionLedgerBuilder.build(...) -> tuple[DetectionDecisionRecord, ...]`.

- [ ] **Step 1: Write failing adapter smoke acceptance test**

Create `tests/acceptance/test_adapter_smoke.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_run_smoke_writes_cleaned_and_audit_artifacts() -> None:
    subprocess.run(["make", "seed"], cwd=ROOT, text=True, capture_output=True, check=True)
    result = subprocess.run(
        [
            "python",
            "-m",
            "handdetect.cli.main",
            "run",
            "--config",
            "configs/smoke-experiment.toml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    marker = "run_id="
    assert marker in result.stdout
    run_id = result.stdout.split(marker, 1)[1].split()[0]
    run_root = ROOT / "runs" / run_id
    cleaned = sorted((run_root / "cleaned").glob("*.json"))
    audit = sorted((run_root / "audit").glob("*.jsonl"))
    assert cleaned
    assert audit
    payload = json.loads(cleaned[0].read_text(encoding="utf-8"))
    assert payload["interpolated_detection_count"] == 0
    assert payload["max_detections_per_frame"] <= 2
```

- [ ] **Step 2: Run the failing adapter smoke test**

Run:

```bash
python -m pytest tests/acceptance/test_adapter_smoke.py -v
```

Expected:

```text
FAILED tests/acceptance/test_adapter_smoke.py::test_run_smoke_writes_cleaned_and_audit_artifacts
```

- [ ] **Step 3: Create stage result models**

Create `src/handdetect/filters/results.py`:

```python
from __future__ import annotations

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict

from handdetect.domain.ids import ClipId


BoolArray = npt.NDArray[np.bool_]
Int32Array = npt.NDArray[np.int32]
Float32Array = npt.NDArray[np.float32]


class GeometricStageResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    clip_id: ClipId
    candidate_mask: BoolArray
    reject_reason_code: Int32Array
    merged_into_index: Int32Array


class TrackBlock(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    clip_id: ClipId
    source_detection_index: Int32Array
    track_id: Int32Array
    track_age_frames: Int32Array
    track_score: Float32Array


class TemporalStageResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    clip_id: ClipId
    keep_mask: BoolArray
    reject_reason_code: Int32Array
    track_id: Int32Array


class SelectedDetectionBlock(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    clip_id: ClipId
    selected_mask: BoolArray
    track_id: Int32Array
    rank_in_frame: Int32Array
```

- [ ] **Step 4: Implement filter registry and geometric filters**

Create `src/handdetect/filters/registry.py`:

```python
from __future__ import annotations

from collections.abc import Callable

from handdetect.domain.enums import FilterName

FilterFactory = Callable[[], object]


class FilterRegistry:
    def __init__(self) -> None:
        self._factories: dict[FilterName, FilterFactory] = {}

    def register(self, name: FilterName, factory: FilterFactory) -> None:
        if name in self._factories:
            raise ValueError(f"filter already registered: {name}")
        self._factories[name] = factory

    def create(self, name: FilterName) -> object:
        try:
            return self._factories[name]()
        except KeyError as exc:
            raise ValueError(f"filter not registered: {name}") from exc
```

Create `src/handdetect/filters/geometric.py`:

```python
from __future__ import annotations

import numpy as np

from handdetect.config.models import AdapterConfig
from handdetect.domain.enums import RejectReason
from handdetect.filters.results import GeometricStageResult
from handdetect.hotpath.blocks import DetectionBlock


REASON_CODE_NONE = 0
REASON_CODE_DUPLICATE = 1
REASON_CODE_SIZE = 2
REASON_CODE_SHAPE = 3


class GeometricFilterPipeline:
    def run(self, block: DetectionBlock, config: AdapterConfig) -> GeometricStageResult:
        count = block.xyxy.shape[0]
        candidate_mask = np.ones(count, dtype=np.bool_)
        reason_code = np.zeros(count, dtype=np.int32)
        merged_into = np.full(count, -1, dtype=np.int32)
        area = self._area(block.xyxy)
        aspect = self._aspect(block.xyxy)
        size_reject = (area < config.min_box_area_px) | (area > config.max_box_area_px)
        shape_reject = (aspect < config.min_aspect_ratio) | (aspect > config.max_aspect_ratio)
        candidate_mask[size_reject] = False
        reason_code[size_reject] = REASON_CODE_SIZE
        candidate_mask[shape_reject] = False
        reason_code[shape_reject] = REASON_CODE_SHAPE
        self._merge_duplicates(block, config.duplicate_iou_threshold, candidate_mask, reason_code, merged_into)
        return GeometricStageResult(
            clip_id=block.clip_id,
            candidate_mask=candidate_mask,
            reject_reason_code=reason_code,
            merged_into_index=merged_into,
        )

    def _area(self, xyxy: np.ndarray) -> np.ndarray:
        width = np.maximum(xyxy[:, 2] - xyxy[:, 0], 0.0)
        height = np.maximum(xyxy[:, 3] - xyxy[:, 1], 0.0)
        return width * height

    def _aspect(self, xyxy: np.ndarray) -> np.ndarray:
        width = np.maximum(xyxy[:, 2] - xyxy[:, 0], 1.0)
        height = np.maximum(xyxy[:, 3] - xyxy[:, 1], 1.0)
        return width / height

    def _merge_duplicates(
        self,
        block: DetectionBlock,
        threshold: float,
        candidate_mask: np.ndarray,
        reason_code: np.ndarray,
        merged_into: np.ndarray,
    ) -> None:
        for frame in np.unique(block.frame_index):
            frame_indexes = np.flatnonzero((block.frame_index == frame) & candidate_mask)
            for left_pos, left_index in enumerate(frame_indexes):
                if not candidate_mask[left_index]:
                    continue
                for right_index in frame_indexes[left_pos + 1 :]:
                    if not candidate_mask[right_index]:
                        continue
                    if self._iou(block.xyxy[left_index], block.xyxy[right_index]) < threshold:
                        continue
                    keep_index = left_index if block.confidence[left_index] >= block.confidence[right_index] else right_index
                    drop_index = right_index if keep_index == left_index else left_index
                    candidate_mask[drop_index] = False
                    reason_code[drop_index] = REASON_CODE_DUPLICATE
                    merged_into[drop_index] = keep_index

    def _iou(self, left: np.ndarray, right: np.ndarray) -> float:
        x1 = max(float(left[0]), float(right[0]))
        y1 = max(float(left[1]), float(right[1]))
        x2 = min(float(left[2]), float(right[2]))
        y2 = min(float(left[3]), float(right[3]))
        inter = max(x2 - x1, 0.0) * max(y2 - y1, 0.0)
        left_area = max(float(left[2] - left[0]), 0.0) * max(float(left[3] - left[1]), 0.0)
        right_area = max(float(right[2] - right[0]), 0.0) * max(float(right[3] - right[1]), 0.0)
        union = left_area + right_area - inter
        return 0.0 if union <= 0.0 else inter / union
```

- [ ] **Step 5: Implement ByteTrack adapter**

Create `src/handdetect/tracking/interfaces.py`:

```python
from __future__ import annotations

from typing import Protocol

from handdetect.config.models import ByteTrackConfig
from handdetect.filters.results import GeometricStageResult, TrackBlock
from handdetect.hotpath.blocks import DetectionBlock


class AssociationAdapter(Protocol):
    def associate(
        self,
        block: DetectionBlock,
        geometric: GeometricStageResult,
        config: ByteTrackConfig,
    ) -> TrackBlock:
        ...
```

Create `src/handdetect/tracking/bytetrack.py`:

```python
from __future__ import annotations

import numpy as np
from trackers import ByteTrackTracker

from handdetect.config.models import ByteTrackConfig
from handdetect.domain.constants import BYTE_TRACK_CLASS_ID
from handdetect.filters.results import GeometricStageResult, TrackBlock
from handdetect.hotpath.blocks import DetectionBlock
from handdetect.tracking.interfaces import AssociationAdapter


class ByteTrackAssociationAdapter(AssociationAdapter):
    def associate(
        self,
        block: DetectionBlock,
        geometric: GeometricStageResult,
        config: ByteTrackConfig,
    ) -> TrackBlock:
        tracker = ByteTrackTracker(
            track_activation_threshold=config.track_activation_threshold,
            minimum_matching_threshold=config.minimum_matching_threshold,
            lost_track_buffer=config.lost_track_buffer,
            frame_rate=config.frame_rate,
        )
        source_indexes: list[int] = []
        track_ids: list[int] = []
        ages: list[int] = []
        scores: list[float] = []
        for frame in np.unique(block.frame_index):
            frame_indexes = np.flatnonzero((block.frame_index == frame) & geometric.candidate_mask)
            tensor = self._frame_tensor(block, frame_indexes)
            tracks = tracker.update(tensor)
            for track in tracks:
                source_index = self._nearest_source_index(block, frame_indexes, np.asarray(track.tlbr, dtype=np.float32))
                source_indexes.append(source_index)
                track_ids.append(int(track.track_id))
                ages.append(int(getattr(track, "tracklet_len", 1)))
                scores.append(float(track.score))
        return TrackBlock(
            clip_id=block.clip_id,
            source_detection_index=np.asarray(source_indexes, dtype=np.int32),
            track_id=np.asarray(track_ids, dtype=np.int32),
            track_age_frames=np.asarray(ages, dtype=np.int32),
            track_score=np.asarray(scores, dtype=np.float32),
        )

    def _frame_tensor(self, block: DetectionBlock, indexes: np.ndarray) -> np.ndarray:
        xyxy = block.xyxy[indexes]
        scores = block.confidence[indexes].reshape(-1, 1)
        classes = np.full((indexes.shape[0], 1), BYTE_TRACK_CLASS_ID, dtype=np.float32)
        return np.concatenate([xyxy, scores, classes], axis=1).astype(np.float32, copy=False)

    def _nearest_source_index(self, block: DetectionBlock, indexes: np.ndarray, xyxy: np.ndarray) -> int:
        centers = (block.xyxy[indexes, :2] + block.xyxy[indexes, 2:]) * 0.5
        target = (xyxy[:2] + xyxy[2:]) * 0.5
        distances = np.sum((centers - target) ** 2, axis=1)
        return int(indexes[int(np.argmin(distances))])
```

- [ ] **Step 6: Implement temporal filters and max-two selector**

Create `src/handdetect/filters/temporal.py`:

```python
from __future__ import annotations

import numpy as np

from handdetect.config.models import AdapterConfig
from handdetect.filters.results import TemporalStageResult, TrackBlock
from handdetect.hotpath.blocks import DetectionBlock

REASON_CODE_NONE = 0
REASON_CODE_DISPLACEMENT = 4
REASON_CODE_UNSUPPORTED = 5
REASON_CODE_STATIC = 6


class TemporalFilterPipeline:
    def run(self, block: DetectionBlock, tracks: TrackBlock, config: AdapterConfig) -> TemporalStageResult:
        keep = np.ones(tracks.source_detection_index.shape[0], dtype=np.bool_)
        reason = np.zeros(tracks.source_detection_index.shape[0], dtype=np.int32)
        short_track = tracks.track_age_frames < config.min_track_length_frames
        keep[short_track] = False
        reason[short_track] = REASON_CODE_UNSUPPORTED
        self._reject_large_jumps(block, tracks, config, keep, reason)
        return TemporalStageResult(clip_id=block.clip_id, keep_mask=keep, reject_reason_code=reason, track_id=tracks.track_id)

    def _reject_large_jumps(
        self,
        block: DetectionBlock,
        tracks: TrackBlock,
        config: AdapterConfig,
        keep: np.ndarray,
        reason: np.ndarray,
    ) -> None:
        for track_id in np.unique(tracks.track_id):
            positions = np.flatnonzero(tracks.track_id == track_id)
            source = tracks.source_detection_index[positions]
            order = np.argsort(block.frame_index[source])
            ordered_positions = positions[order]
            ordered_source = source[order]
            centers = (block.xyxy[ordered_source, :2] + block.xyxy[ordered_source, 2:]) * 0.5
            dt = np.maximum(np.diff(block.timestamp_ns[ordered_source]).astype(np.float32) / 1_000_000_000.0, 1.0 / 30.0)
            speed = np.linalg.norm(np.diff(centers, axis=0), axis=1) / dt
            jump_positions = ordered_positions[1:][speed > config.max_center_speed_px_per_s]
            keep[jump_positions] = False
            reason[jump_positions] = REASON_CODE_DISPLACEMENT
```

Create `src/handdetect/selection/max_two.py`:

```python
from __future__ import annotations

import numpy as np

from handdetect.domain.constants import MAX_HANDS_PER_FRAME
from handdetect.filters.results import SelectedDetectionBlock, TemporalStageResult, TrackBlock
from handdetect.hotpath.blocks import DetectionBlock


class MaxTwoSelector:
    def select(self, block: DetectionBlock, tracks: TrackBlock, temporal: TemporalStageResult) -> SelectedDetectionBlock:
        selected = np.zeros(block.frame_index.shape[0], dtype=np.bool_)
        track_by_source = np.full(block.frame_index.shape[0], -1, dtype=np.int32)
        rank_by_source = np.full(block.frame_index.shape[0], -1, dtype=np.int32)
        live_positions = np.flatnonzero(temporal.keep_mask)
        for frame in np.unique(block.frame_index[tracks.source_detection_index[live_positions]]):
            positions = live_positions[block.frame_index[tracks.source_detection_index[live_positions]] == frame]
            score = tracks.track_score[positions]
            order = positions[np.argsort(score)[::-1]][:MAX_HANDS_PER_FRAME]
            for rank, position in enumerate(order):
                source_index = int(tracks.source_detection_index[position])
                selected[source_index] = True
                track_by_source[source_index] = int(tracks.track_id[position])
                rank_by_source[source_index] = rank
        return SelectedDetectionBlock(clip_id=block.clip_id, selected_mask=selected, track_id=track_by_source, rank_in_frame=rank_by_source)
```

- [ ] **Step 7: Implement audit ledger builder**

Create `src/handdetect/audit/ledger.py`:

```python
from __future__ import annotations

from handdetect.domain.enums import DetectionDecision, FilterName, RejectReason
from handdetect.domain.ids import DetectionId, RunId, TrackId
from handdetect.domain.models import DetectionDecisionRecord
from handdetect.filters.geometric import REASON_CODE_DUPLICATE, REASON_CODE_SHAPE, REASON_CODE_SIZE
from handdetect.filters.results import GeometricStageResult, SelectedDetectionBlock
from handdetect.hotpath.blocks import DetectionBlock


GEOMETRIC_REASON_BY_CODE = {
    REASON_CODE_DUPLICATE: RejectReason.DUPLICATE_OVERLAP,
    REASON_CODE_SIZE: RejectReason.IMPLAUSIBLE_SIZE,
    REASON_CODE_SHAPE: RejectReason.IMPLAUSIBLE_SHAPE,
}


class DecisionLedgerBuilder:
    def build(
        self,
        run_id: RunId,
        block: DetectionBlock,
        geometric: GeometricStageResult,
        selected: SelectedDetectionBlock,
    ) -> tuple[DetectionDecisionRecord, ...]:
        records: list[DetectionDecisionRecord] = []
        for index, detection_id in enumerate(block.detection_ids):
            decision = DetectionDecision.KEPT if bool(selected.selected_mask[index]) else DetectionDecision.REJECTED
            reason = None
            stage = FilterName.MAX_TWO_SELECTOR
            if not bool(geometric.candidate_mask[index]):
                decision = DetectionDecision.MERGED if int(geometric.merged_into_index[index]) >= 0 else DetectionDecision.REJECTED
                reason = GEOMETRIC_REASON_BY_CODE[int(geometric.reject_reason_code[index])]
                stage = FilterName.DUPLICATE_MERGE if reason == RejectReason.DUPLICATE_OVERLAP else FilterName.SIZE_GATE
            records.append(
                DetectionDecisionRecord(
                    run_id=run_id,
                    clip_id=block.clip_id,
                    detection_id=DetectionId(detection_id),
                    frame=block.frame_index[index].item(),
                    decision=decision,
                    stage=stage,
                    reason=reason,
                    track_id=TrackId(int(selected.track_id[index])) if int(selected.track_id[index]) > 0 else None,
                    merged_into=DetectionId(block.detection_ids[int(geometric.merged_into_index[index])]) if int(geometric.merged_into_index[index]) >= 0 else None,
                    timestamp_ns=block.timestamp_ns[index].item(),
                )
            )
        return tuple(records)
```

- [ ] **Step 8: Run smoke test and commit**

Run:

```bash
python -m pytest tests/acceptance/test_adapter_smoke.py -v
make check
```

Expected after Task 4 wires the CLI:

```text
1 passed
```

Commit after Task 4 passes this acceptance test:

```bash
git add src/handdetect/filters src/handdetect/tracking src/handdetect/selection src/handdetect/audit tests/acceptance/test_adapter_smoke.py
git commit -m "feat: add ByteTrack adapter and false-positive filters"
```
