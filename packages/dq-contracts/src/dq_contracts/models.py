from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from dq_contracts.enums import DetectionDecision, FilterName, RejectReason
from dq_contracts.ids import ClipId, DetectionId, FrameIndex, RunId, TimestampNs, TrackId


class BoxXYXY(BaseModel):
    model_config = ConfigDict(frozen=True)

    x1: float
    y1: float
    x2: float
    y2: float


class RawDetection(BaseModel):
    model_config = ConfigDict(frozen=True)

    frame: FrameIndex
    xyxy: BoxXYXY
    confidence: float = Field(ge=0.0, le=1.0)
    class_id: int
    handedness: str


class ValidatedClipPathSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    clip_id: ClipId
    clip_dir: Path
    meta_path: Path
    hand_boxes_path: Path
    frame_ts_path: Path
    vio_pose_path: Path
    video_left_path: Path
    video_right_path: Path


class DetectionDecisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: RunId
    clip_id: ClipId
    detection_id: DetectionId
    frame: FrameIndex
    decision: DetectionDecision
    stage: FilterName
    reason: RejectReason | None
    track_id: TrackId | None
    merged_into: DetectionId | None
    timestamp_ns: TimestampNs


class DatasetMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    clip_id: ClipId
    duration_s: float
    fps: float
    width: int
    height: int
