from __future__ import annotations

import numpy as np
import numpy.typing as npt
from dq_contracts.ids import ClipId
from pydantic import BaseModel, ConfigDict

BoolArray = npt.NDArray[np.bool_]
Int32Array = npt.NDArray[np.int32]
Float32Array = npt.NDArray[np.float32]


class GeometricStageResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    clip_id: ClipId
    candidate_mask: BoolArray
    reject_reason_code: Int32Array
    merged_into_index: Int32Array
    geometry_area: Float32Array | None = None
    geometry_aspect: Float32Array | None = None


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
    static_score: Float32Array | None = None


class SelectedDetectionBlock(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    clip_id: ClipId
    selected_mask: BoolArray
    track_id: Int32Array
    rank_in_frame: Int32Array
