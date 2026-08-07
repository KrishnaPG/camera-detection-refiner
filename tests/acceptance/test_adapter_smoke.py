from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from dq_contracts.enums import DetectionDecision, FilterName, RejectReason
from dq_contracts.ids import ClipId, RunId
from handdetect.audit.ledger import DecisionLedgerBuilder
from handdetect.filters.results import (
    GeometricStageResult,
    SelectedDetectionBlock,
    TemporalStageResult,
    TrackBlock,
)
from handdetect.filters.temporal import REASON_CODE_UNSUPPORTED
from handdetect.hotpath.blocks import DetectionBlock
from handdetect.runtime_paths import runs_root

ROOT = Path(__file__).resolve().parents[2]


def _run_smoke() -> tuple[str, str]:
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
    return suite_id, run_id


def test_run_smoke_writes_cleaned_and_audit_artifacts() -> None:
    suite_id, run_id = _run_smoke()
    run_root = runs_root() / suite_id / run_id
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
