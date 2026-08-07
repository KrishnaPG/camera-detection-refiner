from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class AdapterConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    duplicate_iou_threshold: float = Field(gt=0.0, lt=1.0)
    min_box_area_px: float = Field(gt=0.0)
    max_box_area_px: float = Field(gt=0.0)
    min_aspect_ratio: float = Field(gt=0.0)
    max_aspect_ratio: float = Field(gt=0.0)
    max_center_speed_px_per_s: float = Field(gt=0.0)
    min_track_length_frames: int = Field(ge=1)
    static_camera_motion_px: float = Field(ge=0.0)
    static_box_motion_px: float = Field(ge=0.0)


class ByteTrackConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    track_activation_threshold: float = Field(gt=0.0, lt=1.0)
    minimum_matching_threshold: float = Field(gt=0.0, lt=1.0)
    lost_track_buffer: int = Field(ge=1)
    frame_rate: int = Field(ge=1)


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_root: Path
    runs_root: Path
    max_clip_workers: int = Field(ge=1)
    mlflow_tracking_uri: str
    dvclive_root: Path
    evidently_root: Path
    workbench_host: str = "127.0.0.1"
    workbench_port: int = Field(default=8000, ge=1, le=65535)
    workbench_public_url: str = ""
    mlflow_public_url: str = ""
    fiftyone_public_url: str = ""
    label_studio_url: str = ""
    label_studio_public_url: str = ""
    label_studio_token: str = ""


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    adapter: AdapterConfig
    bytetrack: ByteTrackConfig
    enabled_filters: tuple[str, ...]


class ValidatedExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    runtime: RuntimeConfig
    experiments: tuple[ExperimentConfig, ...]
