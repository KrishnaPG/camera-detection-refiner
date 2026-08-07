from __future__ import annotations

import numpy as np
import numpy.typing as npt
from dq_contracts.ids import ClipId
from pydantic import BaseModel, ConfigDict

Float32Array = npt.NDArray[np.float32]
Int32Array = npt.NDArray[np.int32]
Int64Array = npt.NDArray[np.int64]


class DetectionBlock(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    clip_id: ClipId
    detection_ids: tuple[str, ...]
    frame_index: Int32Array
    xyxy: Float32Array
    confidence: Float32Array
    class_id: Int32Array
    handedness: tuple[str, ...]
    timestamp_ns: Int64Array

    @property
    def detection_count(self) -> int:
        return int(self.detection_ids.__len__())

    def frame_indexes(self) -> Int32Array:
        return self.frame_index
