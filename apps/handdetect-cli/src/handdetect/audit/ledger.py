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
    TrackBlock,
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
        tracks: TrackBlock,
        temporal: TemporalStageResult,
        selected: SelectedDetectionBlock,
    ) -> tuple[DetectionDecisionRecord, ...]:
        records: list[DetectionDecisionRecord] = []
        keep_by_source = selected.selected_mask
        temporal_reason_by_source, tracked_by_source, track_id_by_source = (
            self._track_context_by_source(
                block.detection_count,
                tracks,
                temporal,
            )
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
                    if (
                        reason is None
                        and reason_code == 0
                        and temporal_reason_by_source[index] == 0
                        and tracked_by_source[index]
                    ):
                        reason = RejectReason.OVER_MAX_HANDS
                    stage = _stage_from_reason(reason_code, reason)

            merged = int(geometric.merged_into_index[index])
            track_id = int(track_id_by_source[index])
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

    def _track_context_by_source(
        self,
        detection_count: int,
        tracks: TrackBlock,
        temporal: TemporalStageResult,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        reason_by_source = np.zeros(detection_count, dtype=np.int32)
        tracked_by_source = np.zeros(detection_count, dtype=np.bool_)
        track_id_by_source = np.full(detection_count, -1, dtype=np.int32)
        for position, source_index in enumerate(tracks.source_detection_index.tolist()):
            if position >= temporal.reject_reason_code.size:
                break
            reason_by_source[source_index] = int(temporal.reject_reason_code[position])
            tracked_by_source[source_index] = True
            track_id_by_source[source_index] = int(tracks.track_id[position])
        return reason_by_source, tracked_by_source, track_id_by_source


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
