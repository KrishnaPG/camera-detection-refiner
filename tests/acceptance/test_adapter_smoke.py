from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import supervision as sv
from dq_contracts.enums import DetectionDecision, FilterName, RejectReason
from dq_contracts.ids import ClipId, RunId
from handdetect.audit.ledger import DecisionLedgerBuilder
from handdetect.filters.results import (
    GeometricStageResult,
    SelectedDetectionBlock,
    TemporalStageResult,
    TrackBlock,
)
from handdetect.filters.temporal import REASON_CODE_UNSUPPORTED, TemporalFilterPipeline
from handdetect.hotpath.blocks import DetectionBlock
from handdetect.pipeline.clip_runner import ClipRunner
from handdetect.runtime_paths import runs_root
from handdetect.tracking.bytetrack import ByteTrackAssociationAdapter
from handdetect_domain.config import (
    AdapterConfig,
    ByteTrackConfig,
    ExperimentConfig,
)
from run_artifacts.store import RunArtifactStore

ROOT = Path(__file__).resolve().parents[2]


def _run_smoke() -> tuple[str, str, Path]:
    result = subprocess.run(
        ["python", "-m", "handdetect.cli.main", "run", "--config", "configs/smoke-experiment.toml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    suite_id = result.stdout.split("suite_id=", 1)[1].split()[0]
    run_id = result.stdout.split("run_id=", 1)[1].split()[0]
    report_path = Path(result.stdout.split("report=", 1)[1].splitlines()[0])
    run_root = report_path.parent.parent
    assert run_root.exists(), result.stdout
    return suite_id, run_id, run_root


def test_run_smoke_writes_cleaned_and_audit_artifacts() -> None:
    suite_id, run_id, run_root = _run_smoke()
    assert run_root == runs_root() / suite_id / run_id
    cleaned = sorted((run_root / "cleaned").glob("*.json"))
    audit = sorted((run_root / "audit").glob("*.jsonl"))
    assert cleaned
    assert audit
    payload = json.loads(cleaned[0].read_text(encoding="utf-8"))
    assert payload["interpolated_detection_count"] == 0
    assert payload["max_detections_per_frame"] <= 2


def test_decision_ledger_preserves_temporal_and_over_cap_reasons() -> None:
    records = DecisionLedgerBuilder().build(
        RunId("run-20260807-000001"),
        DetectionBlock(
            clip_id=ClipId("clip-1"),
            detection_ids=("det-0", "det-1", "det-2", "det-3"),
            frame_index=np.array([0, 0, 0, 0], dtype=np.int32),
            timestamp_ns=np.array([0, 1, 2, 3], dtype=np.int64),
            xyxy=np.array(
                [
                    [0.0, 0.0, 1.0, 1.0],
                    [1.0, 1.0, 2.0, 2.0],
                    [2.0, 2.0, 3.0, 3.0],
                    [3.0, 3.0, 4.0, 4.0],
                ],
                dtype=np.float32,
            ),
            confidence=np.array([0.9, 0.9, 0.8, 0.7], dtype=np.float32),
            class_id=np.zeros(4, dtype=np.int32),
            handedness=("left", "left", "right", "right"),
        ),
        GeometricStageResult(
            clip_id=ClipId("clip-1"),
            candidate_mask=np.array([True, True, True, True]),
            reject_reason_code=np.zeros(4, dtype=np.int32),
            merged_into_index=np.full(4, -1, dtype=np.int32),
        ),
        TrackBlock(
            clip_id=ClipId("clip-1"),
            source_detection_index=np.array([0, 1, 2, 3], dtype=np.int32),
            track_id=np.array([10, 11, 12, 13], dtype=np.int32),
            track_age_frames=np.array([1, 2, 2, 2], dtype=np.int32),
            track_score=np.array([0.6, 0.9, 0.8, 0.7], dtype=np.float32),
        ),
        TemporalStageResult(
            clip_id=ClipId("clip-1"),
            keep_mask=np.array([False, True, True, True]),
            reject_reason_code=np.array([REASON_CODE_UNSUPPORTED, 0, 0, 0], dtype=np.int32),
            track_id=np.array([10, 11, 12, 13], dtype=np.int32),
            static_score=np.zeros(4, dtype=np.float32),
        ),
        SelectedDetectionBlock(
            clip_id=ClipId("clip-1"),
            selected_mask=np.array([False, True, True, False]),
            track_id=np.array([-1, 11, 12, -1], dtype=np.int32),
            rank_in_frame=np.array([-1, 0, 1, -1], dtype=np.int32),
        ),
    )

    by_detection = {str(record.detection_id): record for record in records}
    assert by_detection["det-0"].decision == DetectionDecision.REJECTED
    assert by_detection["det-0"].stage == FilterName.TRACK_SUPPORT_GATE
    assert by_detection["det-0"].reason == RejectReason.UNSUPPORTED_TRACK
    assert by_detection["det-3"].decision == DetectionDecision.REJECTED
    assert by_detection["det-3"].stage == FilterName.MAX_TWO_SELECTOR
    assert by_detection["det-3"].reason == RejectReason.OVER_MAX_HANDS


def test_temporal_track_support_keeps_all_observations_for_supported_track() -> None:
    block = DetectionBlock(
        clip_id=ClipId("clip-1"),
        detection_ids=("det-0", "det-1", "det-2"),
        frame_index=np.array([0, 1, 2], dtype=np.int32),
        timestamp_ns=np.array([0, 1_000_000_000, 2_000_000_000], dtype=np.int64),
        xyxy=np.array(
            [
                [0.0, 0.0, 10.0, 10.0],
                [2.0, 0.0, 12.0, 10.0],
                [4.0, 0.0, 14.0, 10.0],
            ],
            dtype=np.float32,
        ),
        confidence=np.array([0.9, 0.9, 0.9], dtype=np.float32),
        class_id=np.zeros(3, dtype=np.int32),
        handedness=("left", "left", "left"),
    )
    tracks = TrackBlock(
        clip_id=ClipId("clip-1"),
        source_detection_index=np.array([0, 1, 2], dtype=np.int32),
        track_id=np.array([42, 42, 42], dtype=np.int32),
        track_age_frames=np.array([1, 2, 3], dtype=np.int32),
        track_score=np.array([0.9, 0.9, 0.9], dtype=np.float32),
    )
    config = AdapterConfig(
        duplicate_iou_threshold=0.5,
        min_box_area_px=1.0,
        max_box_area_px=10_000.0,
        min_aspect_ratio=0.1,
        max_aspect_ratio=10.0,
        max_center_speed_px_per_s=100.0,
        min_track_length_frames=3,
        static_camera_motion_px=0.0,
        static_box_motion_px=0.0,
    )

    result = TemporalFilterPipeline().run(block, tracks, config)

    assert result.keep_mask.tolist() == [True, True, True]
    assert result.reject_reason_code.tolist() == [0, 0, 0]


def test_bytetrack_association_preserves_source_indexes_when_tracker_reorders(
    monkeypatch,
) -> None:
    block = DetectionBlock(
        clip_id=ClipId("clip-1"),
        detection_ids=("det-0", "det-1"),
        frame_index=np.array([0, 0], dtype=np.int32),
        timestamp_ns=np.array([0, 0], dtype=np.int64),
        xyxy=np.array(
            [[0.0, 0.0, 10.0, 10.0], [100.0, 100.0, 120.0, 120.0]],
            dtype=np.float32,
        ),
        confidence=np.array([0.4, 0.9], dtype=np.float32),
        class_id=np.zeros(2, dtype=np.int32),
        handedness=("left", "right"),
    )
    geometric = GeometricStageResult(
        clip_id=ClipId("clip-1"),
        candidate_mask=np.array([True, True]),
        reject_reason_code=np.zeros(2, dtype=np.int32),
        merged_into_index=np.full(2, -1, dtype=np.int32),
    )

    class ReorderingTracker:
        def __init__(self, **kwargs: object) -> None:
            del kwargs

        def update(self, detections: sv.Detections, timestamp: float) -> sv.Detections:
            del timestamp
            reordered = detections[np.array([1, 0])]
            reordered.tracker_id = np.array([22, 11], dtype=np.int32)
            return reordered

    monkeypatch.setattr("mot_bytetrack.bytetrack.ByteTrackTracker", ReorderingTracker)

    tracks = ByteTrackAssociationAdapter().associate(
        block,
        geometric,
        ByteTrackConfig(
            track_activation_threshold=0.2,
            minimum_matching_threshold=0.1,
            lost_track_buffer=30,
            frame_rate=30,
        ),
    )

    assert tracks.source_detection_index.tolist() == [1, 0]
    assert tracks.track_id.tolist() == [22, 11]


def test_disabled_filters_use_passthrough_stages(monkeypatch, tmp_path) -> None:
    block = DetectionBlock(
        clip_id=ClipId("clip-1"),
        detection_ids=("det-0", "det-1", "det-2"),
        frame_index=np.array([0, 0, 0], dtype=np.int32),
        timestamp_ns=np.array([0, 0, 0], dtype=np.int64),
        xyxy=np.array(
            [
                [0.0, 0.0, 10.0, 10.0],
                [10.0, 10.0, 20.0, 20.0],
                [20.0, 20.0, 30.0, 30.0],
            ],
            dtype=np.float32,
        ),
        confidence=np.array([0.4, 0.8, 0.6], dtype=np.float32),
        class_id=np.zeros(3, dtype=np.int32),
        handedness=("left", "left", "right"),
    )

    class FakePaths:
        clip_id = ClipId("clip-1")

    class FakeParser:
        def parse_clip(self, paths: object) -> object:
            del paths
            return object()

    class FakeColumnBuilder:
        def build(self, bundle: object) -> DetectionBlock:
            del bundle
            return block

    def fail_stage(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("disabled stage should not run")

    monkeypatch.setattr("experiment_runner.clip_runner.JsonBoundaryParser", FakeParser)
    monkeypatch.setattr("experiment_runner.clip_runner.ClipColumnBuilder", FakeColumnBuilder)
    monkeypatch.setattr("experiment_runner.clip_runner.GeometricFilterPipeline.run", fail_stage)
    monkeypatch.setattr(
        "experiment_runner.clip_runner.ByteTrackAssociationAdapter.associate", fail_stage
    )
    monkeypatch.setattr("experiment_runner.clip_runner.TemporalFilterPipeline.run", fail_stage)
    monkeypatch.setattr("experiment_runner.clip_runner.MaxTwoSelector.select", fail_stage)

    summary = ClipRunner().run_clip(
        FakePaths(),
        RunId("run-1"),
        ExperimentConfig(
            name="no_filters",
            enabled_filters=(),
            adapter=AdapterConfig(
                duplicate_iou_threshold=0.5,
                min_box_area_px=1.0,
                max_box_area_px=10_000.0,
                min_aspect_ratio=0.1,
                max_aspect_ratio=10.0,
                max_center_speed_px_per_s=100.0,
                min_track_length_frames=3,
                static_camera_motion_px=0.0,
                static_box_motion_px=0.0,
            ),
            bytetrack=ByteTrackConfig(
                track_activation_threshold=0.2,
                minimum_matching_threshold=0.1,
                lost_track_buffer=30,
                frame_rate=30,
            ),
        ),
        RunArtifactStore.open(tmp_path, "suite-1", "run-1"),
    )

    assert summary.selected_detection_count == 3
    cleaned = json.loads(
        (tmp_path / "suite-1" / "run-1" / "cleaned" / "clip-1.json").read_text(encoding="utf-8")
    )
    assert cleaned["max_detections_per_frame"] == 3
