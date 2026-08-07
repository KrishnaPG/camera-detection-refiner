from __future__ import annotations

import numpy as np
from dq_contracts.enums import RejectReason
from handdetect_domain.config import AdapterConfig
from vision_columnar.blocks import DetectionBlock

from dq_filter_kit.results import GeometricStageResult

REASON_CODE_NONE = 0
REASON_CODE_DUPLICATE = 1
REASON_CODE_SIZE = 2
REASON_CODE_SHAPE = 3

GEOMETRIC_REASON_BY_CODE = {
    REASON_CODE_DUPLICATE: RejectReason.DUPLICATE_OVERLAP,
    REASON_CODE_SIZE: RejectReason.IMPLAUSIBLE_SIZE,
    REASON_CODE_SHAPE: RejectReason.IMPLAUSIBLE_SHAPE,
}


class GeometricFilterPipeline:
    def run(self, block: DetectionBlock, config: AdapterConfig) -> GeometricStageResult:
        count = block.xyxy.shape[0]
        candidate_mask = np.ones(count, dtype=np.bool_)
        reason_code = np.zeros(count, dtype=np.int32)
        merged_into = np.full(count, -1, dtype=np.int32)
        area = self._area(block.xyxy).astype(np.float32, copy=False)
        aspect = self._aspect(block.xyxy).astype(np.float32, copy=False)

        if count == 0:
            return GeometricStageResult(
                clip_id=block.clip_id,
                candidate_mask=candidate_mask,
                reject_reason_code=reason_code,
                merged_into_index=merged_into,
                geometry_area=area,
                geometry_aspect=aspect,
            )

        size_reject = (area < config.min_box_area_px) | (area > config.max_box_area_px)
        shape_reject = (aspect < config.min_aspect_ratio) | (aspect > config.max_aspect_ratio)
        candidate_mask[size_reject] = False
        reason_code[size_reject] = REASON_CODE_SIZE
        candidate_mask[shape_reject] = False
        reason_code[shape_reject] = REASON_CODE_SHAPE

        self._merge_duplicates(
            block, config.duplicate_iou_threshold, candidate_mask, reason_code, merged_into
        )
        return GeometricStageResult(
            clip_id=block.clip_id,
            candidate_mask=candidate_mask,
            reject_reason_code=reason_code,
            merged_into_index=merged_into,
            geometry_area=area,
            geometry_aspect=aspect,
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
            for local_left, left_index in enumerate(frame_indexes):
                if not candidate_mask[left_index]:
                    continue
                for right_index in frame_indexes[local_left + 1 :]:
                    if not candidate_mask[right_index]:
                        continue
                    if self._iou(block.xyxy[left_index], block.xyxy[right_index]) < threshold:
                        continue
                    keep_index = (
                        left_index
                        if block.confidence[left_index] >= block.confidence[right_index]
                        else right_index
                    )
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


def reject_reason_from_code(code: int) -> RejectReason | None:
    if code == REASON_CODE_DUPLICATE:
        return RejectReason.DUPLICATE_OVERLAP
    if code == REASON_CODE_SIZE:
        return RejectReason.IMPLAUSIBLE_SIZE
    if code == REASON_CODE_SHAPE:
        return RejectReason.IMPLAUSIBLE_SHAPE
    return None
