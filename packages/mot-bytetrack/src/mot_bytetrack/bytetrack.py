from __future__ import annotations

import numpy as np
import supervision as sv
from dq_filter_kit.results import GeometricStageResult, TrackBlock
from handdetect_domain.config import ByteTrackConfig
from mot_interfaces.interfaces import AssociationAdapter
from trackers import ByteTrackTracker
from vision_columnar.blocks import DetectionBlock


class ByteTrackTensorScratch:
    """Reusable frame-local buffers for tracker inputs."""

    def __init__(self, capacity: int) -> None:
        self.xyxy = np.empty((capacity, 4), dtype=np.float32)
        self.confidence = np.empty(capacity, dtype=np.float32)
        self.class_id = np.zeros(capacity, dtype=np.int32)

    def build(self, block: DetectionBlock, indexes: np.ndarray) -> sv.Detections:
        length = int(indexes.shape[0])
        self.xyxy[:length] = block.xyxy[indexes]
        self.confidence[:length] = block.confidence[indexes]
        return sv.Detections(
            xyxy=self.xyxy[:length],
            confidence=self.confidence[:length],
            class_id=self.class_id[:length],
            data={"source_detection_index": indexes.astype(np.int32, copy=False)},
        )


class ByteTrackAssociationAdapter(AssociationAdapter):
    def associate(
        self,
        block: DetectionBlock,
        geometric: GeometricStageResult,
        config: ByteTrackConfig,
    ) -> TrackBlock:
        candidate_count = int(geometric.candidate_mask.sum())
        if candidate_count == 0:
            return self._empty(block)

        tracker = ByteTrackTracker(
            lost_track_buffer=config.lost_track_buffer,
            frame_rate=float(config.frame_rate),
            track_activation_threshold=config.track_activation_threshold,
            minimum_iou_threshold=config.minimum_matching_threshold,
            minimum_consecutive_frames=1,
        )
        scratch = ByteTrackTensorScratch(self._max_frame_candidates(block, geometric))
        source_indexes: list[int] = []
        track_ids: list[int] = []
        ages: list[int] = []
        scores: list[float] = []

        for frame in np.unique(block.frame_index):
            frame_indexes = np.flatnonzero((block.frame_index == frame) & geometric.candidate_mask)
            if frame_indexes.size == 0:
                continue
            detections = scratch.build(block, frame_indexes)
            tracked = tracker.update(detections, timestamp=float(frame))
            tracked_ids = (
                tracked.tracker_id
                if tracked.tracker_id is not None
                else np.full(
                    len(tracked),
                    -1,
                    dtype=np.int32,
                )
            )
            tracked_source_indexes = tracked.get_data("source_detection_index")
            for local_index, tracker_id in enumerate(tracked_ids.tolist()):
                if int(tracker_id) < 0:
                    continue
                source_indexes.append(int(tracked_source_indexes[local_index]))
                track_ids.append(int(tracker_id))
                ages.append(self._track_age(track_ids, int(tracker_id)))
                scores.append(float(tracked.confidence[local_index]))

        if not source_indexes:
            return self._empty(block)

        return TrackBlock(
            clip_id=block.clip_id,
            source_detection_index=np.asarray(source_indexes, dtype=np.int32),
            track_id=np.asarray(track_ids, dtype=np.int32),
            track_age_frames=np.asarray(ages, dtype=np.int32),
            track_score=np.asarray(scores, dtype=np.float32),
        )

    def _empty(self, block: DetectionBlock) -> TrackBlock:
        return TrackBlock(
            clip_id=block.clip_id,
            source_detection_index=np.empty(0, dtype=np.int32),
            track_id=np.empty(0, dtype=np.int32),
            track_age_frames=np.empty(0, dtype=np.int32),
            track_score=np.empty(0, dtype=np.float32),
        )

    def _max_frame_candidates(self, block: DetectionBlock, geometric: GeometricStageResult) -> int:
        frame_counts = np.bincount(block.frame_index[geometric.candidate_mask])
        return int(frame_counts.max(initial=1))

    def _track_age(self, seen_track_ids: list[int], track_id: int) -> int:
        return seen_track_ids.count(track_id)
