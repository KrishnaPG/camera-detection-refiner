from __future__ import annotations

import numpy as np
from dq_filter_kit.results import SelectedDetectionBlock, TemporalStageResult, TrackBlock
from handdetect_domain.constants import MAX_HANDS_PER_FRAME
from vision_columnar.blocks import DetectionBlock


class MaxTwoSelector:
    def select(
        self, block: DetectionBlock, tracks: TrackBlock, temporal: TemporalStageResult
    ) -> SelectedDetectionBlock:
        selected = np.zeros(block.frame_index.shape[0], dtype=np.bool_)
        track_by_source = np.full(block.frame_index.shape[0], -1, dtype=np.int32)
        rank_by_source = np.full(block.frame_index.shape[0], -1, dtype=np.int32)

        if temporal.keep_mask.size == 0:
            return SelectedDetectionBlock(
                clip_id=block.clip_id,
                selected_mask=selected,
                track_id=track_by_source,
                rank_in_frame=rank_by_source,
            )

        live_positions = np.flatnonzero(temporal.keep_mask)
        live_frames = block.frame_index[tracks.source_detection_index[live_positions]]
        for frame in np.unique(live_frames):
            positions = live_positions[live_frames == frame]
            score = tracks.track_score[positions]
            order = positions[np.argsort(score)[::-1]][:MAX_HANDS_PER_FRAME]
            for rank, position in enumerate(order):
                source_index = int(tracks.source_detection_index[position])
                selected[source_index] = True
                track_by_source[source_index] = int(tracks.track_id[position])
                rank_by_source[source_index] = rank

        return SelectedDetectionBlock(
            clip_id=block.clip_id,
            selected_mask=selected,
            track_id=track_by_source,
            rank_in_frame=rank_by_source,
        )
