from __future__ import annotations

import json
from pathlib import Path

from dq_contracts.ids import ClipId
from dq_contracts.models import ValidatedClipPathSet
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class RawFrameDetection(BaseModel):
    model_config = ConfigDict(frozen=True)

    xyxy: tuple[float, float, float, float]
    confidence: float = Field(ge=0.0, le=1.0)
    class_id: int = Field(alias="class")
    handedness: str


class RawFramePayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    frame: int = Field(ge=0)
    detections: tuple[RawFrameDetection, ...] = ()


class ValidatedHandBoxes(BaseModel):
    model_config = ConfigDict(frozen=True)

    detector: str
    eye: str
    video_frame_count: int = Field(gt=0)
    total_detections: int = Field(ge=0)
    frames: tuple[RawFramePayload, ...]

    @model_validator(mode="after")
    def check_count(self) -> ValidatedHandBoxes:
        total = sum(len(frame.detections) for frame in self.frames)
        if self.total_detections != total:
            raise ValueError(
                "total_detections must match detections in frames",
            )
        return self


class ValidatedFrameTimestamps(BaseModel):
    model_config = ConfigDict(frozen=True)

    cid: ClipId
    fps: float
    frame_count: int = Field(gt=0)
    frame_ts: dict[str, int]


class ValidatedVioPose(BaseModel):
    model_config = ConfigDict(frozen=True)

    t: tuple[float, ...]
    x: tuple[float, ...]
    y: tuple[float, ...]
    z: tuple[float, ...]
    roll: tuple[float, ...]
    pitch: tuple[float, ...]
    yaw: tuple[float, ...]

    @model_validator(mode="after")
    def lengths_match(self) -> ValidatedVioPose:
        lengths = {
            len(self.t),
            len(self.x),
            len(self.y),
            len(self.z),
            len(self.roll),
            len(self.pitch),
            len(self.yaw),
        }
        if len(lengths) != 1:
            raise ValueError("vio pose arrays must have equal lengths")
        return self


class ValidatedClipMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    cid: ClipId
    duration_s: float
    fps: float
    width: int
    height: int


class ValidatedClipBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    paths: ValidatedClipPathSet
    meta: ValidatedClipMeta
    hand_boxes: ValidatedHandBoxes
    frame_ts: ValidatedFrameTimestamps
    vio_pose: ValidatedVioPose


class ClipParseError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class JsonBoundaryParser:
    def parse_clip(self, paths: ValidatedClipPathSet) -> ValidatedClipBundle:
        try:
            meta = ValidatedClipMeta.model_validate(self._read_json(paths.meta_path))
            hand_boxes = ValidatedHandBoxes.model_validate(self._read_json(paths.hand_boxes_path))
            frame_ts = ValidatedFrameTimestamps.model_validate(self._read_json(paths.frame_ts_path))
            vio_pose = ValidatedVioPose.model_validate(self._read_json(paths.vio_pose_path))
        except (OSError, ValidationError, json.JSONDecodeError) as exc:  # type: ignore[union-attr]
            raise ClipParseError(f"failed to parse clip {paths.clip_id}: {exc}") from exc

        if meta.cid != paths.clip_id or frame_ts.cid != paths.clip_id:
            raise ClipParseError(f"clip id mismatch for {paths.clip_id}")

        return ValidatedClipBundle(
            paths=paths,
            meta=meta,
            hand_boxes=hand_boxes,
            frame_ts=frame_ts,
            vio_pose=vio_pose,
        )

    def _read_json(self, path: Path) -> object:
        return json.loads(path.read_text(encoding="utf-8"))
