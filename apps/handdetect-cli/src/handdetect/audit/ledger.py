from __future__ import annotations

import numpy as np
from dq_contracts.enums import DetectionDecision, FilterName, RejectReason
from dq_contracts.ids import DetectionId, RunId, TrackId
from dq_contracts.models import DetectionDecisionRecord
from handdetect.filters.geometric import (
    GEOMETRIC_REASON_BY_CODE,
    REASON_CODE_DUPLICATE,
    REASON_CODE_SHAPE,
    REASON_CODE_SIZE,
)
from handdetect.filters.results import (
    GeometricStageResult,
    SelectedDetectionBlock,
    TemporalStageResult,
)
from handdetect.filters.temporal import (
    REASON_CODE_DISPLACEMENT,
    REASON_CODE_STATIC,
    REASON_CODE_UNSUPPORTED,
)
from handdetect.hotpath.blocks import DetectionBlock


class DecisionLedgerBuilder:
    def build(
        self,
        run_id: RunId,
        block: DetectionBlock,
        geometric: GeometricStageResult,
        temporal: TemporalStageResult,
        selected: SelectedDetectionBlock,
    ) -> tuple[DetectionDecisionRecord, ...]:
        records: list[DetectionDecisionRecord] = []
        keep_by_source = selected.selected_mask
        temporal_reason_by_source = self._temporal_reason_by_source(
            block.detection_count, temporal, selected
        )

        for index, detection_id in enumerate(block.detection_ids):
            if index >= len(keep_by_source):
                continue
            if bool(keep_by_source[index]):
                decision = DetectionDecision.KEPT
                stage = FilterName.MAX_TWO_SELECTOR
                reason = None
            else:
                decision = DetectionDecision.REJECTED
                merged_index = int(geometric.merged_into_index[index])
                if merged_index >= 0:
                    decision = DetectionDecision.MERGED
                    reason = GEOMETRIC_REASON_BY_CODE.get(int(geometric.reject_reason_code[index]))
                    stage = FilterName.DUPLICATE_MERGE
                else:
                    reason_code = int(geometric.reject_reason_code[index])
                    reason = _reason_from_temporal_or_geometric(
                        reason_code,
                        temporal_reason_by_source[index],
                    )
                    stage = _stage_from_reason(reason_code, reason)

            merged = int(geometric.merged_into_index[index])
            track_id = int(selected.track_id[index])
            records.append(
                DetectionDecisionRecord(
                    run_id=run_id,
                    clip_id=block.clip_id,
                    detection_id=DetectionId(detection_id),
                    frame=block.frame_index[index].item(),
                    decision=decision,
                    stage=stage,
                    reason=reason,
                    track_id=TrackId(track_id) if track_id >= 0 else None,
                    merged_into=DetectionId(block.detection_ids[merged]) if merged >= 0 else None,
                    timestamp_ns=block.timestamp_ns[index].item(),
                )
            )

        return tuple(records)

    def _temporal_reason_by_source(
        self,
        detection_count: int,
        temporal: TemporalStageResult,
        selected: SelectedDetectionBlock,
    ) -> np.ndarray:
        reason_by_source = np.zeros(detection_count, dtype=np.int32)
        tracked_sources = np.flatnonzero(selected.track_id >= 0)
        for position, source_index in enumerate(tracked_sources.tolist()):
            if position >= temporal.reject_reason_code.size:
                break
            reason_by_source[source_index] = int(temporal.reject_reason_code[position])
        return reason_by_source


def _reason_from_temporal_or_geometric(
    reason_code: int,
    temporal_reason: int,
) -> RejectReason | None:
    if reason_code == REASON_CODE_SIZE:
        return RejectReason.IMPLAUSIBLE_SIZE
    if reason_code == REASON_CODE_SHAPE:
        return RejectReason.IMPLAUSIBLE_SHAPE
    if reason_code == REASON_CODE_DUPLICATE:
        return RejectReason.DUPLICATE_OVERLAP
    if reason_code == REASON_CODE_DISPLACEMENT:
        return RejectReason.IMPLAUSIBLE_DISPLACEMENT
    if reason_code == REASON_CODE_STATIC:
        return RejectReason.STATIC_SCENE
    if reason_code == REASON_CODE_UNSUPPORTED:
        return RejectReason.UNSUPPORTED_TRACK

    if temporal_reason == REASON_CODE_DISPLACEMENT:
        return RejectReason.IMPLAUSIBLE_DISPLACEMENT
    if temporal_reason == REASON_CODE_STATIC:
        return RejectReason.STATIC_SCENE
    if temporal_reason == REASON_CODE_UNSUPPORTED:
        return RejectReason.UNSUPPORTED_TRACK
    return None


def _stage_from_reason(reason_code: int, reason: RejectReason | None) -> FilterName:
    if reason_code == REASON_CODE_DISPLACEMENT:
        return FilterName.DISPLACEMENT_GATE
    if reason_code == REASON_CODE_STATIC:
        return FilterName.STATIC_SCENE_GATE
    if reason_code == REASON_CODE_UNSUPPORTED:
        return FilterName.TRACK_SUPPORT_GATE
    if reason_code == REASON_CODE_DUPLICATE:
        return FilterName.DUPLICATE_MERGE
    if reason_code == REASON_CODE_SIZE:
        return FilterName.SIZE_GATE
    if reason_code == REASON_CODE_SHAPE:
        return FilterName.SHAPE_GATE
    if reason is None:
        return FilterName.MAX_TWO_SELECTOR
    if reason == RejectReason.IMPLAUSIBLE_DISPLACEMENT:
        return FilterName.DISPLACEMENT_GATE
    if reason == RejectReason.STATIC_SCENE:
        return FilterName.STATIC_SCENE_GATE
    if reason == RejectReason.UNSUPPORTED_TRACK:
        return FilterName.TRACK_SUPPORT_GATE
    return FilterName.MAX_TWO_SELECTOR
