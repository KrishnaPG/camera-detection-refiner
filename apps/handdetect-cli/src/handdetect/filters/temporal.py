from __future__ import annotations

import numpy as np
from dq_contracts.enums import RejectReason
from handdetect.filters.results import TemporalStageResult, TrackBlock
from handdetect.hotpath.blocks import DetectionBlock
from handdetect_domain.config import AdapterConfig

REASON_CODE_NONE = 0
REASON_CODE_DISPLACEMENT = 4
REASON_CODE_UNSUPPORTED = 5
REASON_CODE_STATIC = 6


def reject_reason_from_code(code: int) -> RejectReason | None:
    if code == REASON_CODE_DISPLACEMENT:
        return RejectReason.IMPLAUSIBLE_DISPLACEMENT
    if code == REASON_CODE_UNSUPPORTED:
        return RejectReason.UNSUPPORTED_TRACK
    if code == REASON_CODE_STATIC:
        return RejectReason.STATIC_SCENE
    return None


class TemporalFilterPipeline:
    """Apply temporal rules that depend on per-track motion and persistence."""

    def run(
        self, block: DetectionBlock, tracks: TrackBlock, config: AdapterConfig
    ) -> TemporalStageResult:
        if tracks.source_detection_index.size == 0:
            return TemporalStageResult(
                clip_id=block.clip_id,
                keep_mask=np.empty(0, dtype=np.bool_),
                reject_reason_code=np.empty(0, dtype=np.int32),
                track_id=np.empty(0, dtype=np.int32),
                static_score=np.empty(0, dtype=np.float32),
            )

        keep = np.ones(tracks.source_detection_index.shape[0], dtype=np.bool_)
        reason = np.zeros(tracks.source_detection_index.shape[0], dtype=np.int32)
        static_scores = np.zeros(tracks.source_detection_index.shape[0], dtype=np.float32)

        short_track = tracks.track_age_frames < config.min_track_length_frames
        keep[short_track] = False
        reason[short_track] = REASON_CODE_UNSUPPORTED

        self._reject_large_jumps(block, tracks, config, keep, reason)
        self._reject_static_tracks(block, tracks, config, keep, reason, static_scores)

        return TemporalStageResult(
            clip_id=block.clip_id,
            keep_mask=keep,
            reject_reason_code=reason,
            track_id=tracks.track_id,
            static_score=static_scores,
        )

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
            if positions.size < 2:
                continue
            source = tracks.source_detection_index[positions]
            source = np.asarray(source, dtype=np.int32)
            order = np.argsort(block.frame_index[source])
            ordered_positions = positions[order]
            ordered_source = source[order]

            centers = (block.xyxy[ordered_source, :2] + block.xyxy[ordered_source, 2:]) * 0.5
            frame_delta = np.diff(block.timestamp_ns[ordered_source]).astype(np.float32)
            frame_delta = np.maximum(frame_delta, 1e-6)
            dxy = np.linalg.norm(np.diff(centers, axis=0), axis=1)
            speed = dxy / (frame_delta / 1_000_000_000.0)
            jump_positions = ordered_positions[1:][speed > config.max_center_speed_px_per_s]
            keep[jump_positions] = False
            reason[jump_positions] = REASON_CODE_DISPLACEMENT

    def _reject_static_tracks(
        self,
        block: DetectionBlock,
        tracks: TrackBlock,
        config: AdapterConfig,
        keep: np.ndarray,
        reason: np.ndarray,
        static_scores: np.ndarray,
    ) -> None:
        if tracks.source_detection_index.size == 0:
            return

        for track_id in np.unique(tracks.track_id):
            positions = np.flatnonzero(tracks.track_id == track_id)
            if positions.size < 2:
                continue
            source = tracks.source_detection_index[positions]
            source = np.asarray(source, dtype=np.int32)
            order = np.argsort(block.frame_index[source])
            ordered_positions = positions[order]
            ordered_source = source[order]

            centers = (block.xyxy[ordered_source, :2] + block.xyxy[ordered_source, 2:]) * 0.5
            bbox_motion = (
                np.mean(np.linalg.norm(np.diff(centers, axis=0), axis=1)) if centers.size else 0.0
            )
            static_scores[ordered_positions] = float(bbox_motion)
            if bbox_motion < config.static_box_motion_px:
                keep[ordered_positions] = False
                reason[ordered_positions] = REASON_CODE_STATIC
