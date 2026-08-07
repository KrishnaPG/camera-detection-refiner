from __future__ import annotations

from enum import StrEnum


class DetectionDecision(StrEnum):
    KEPT = "kept"
    MERGED = "merged"
    REJECTED = "rejected"


class RejectReason(StrEnum):
    DUPLICATE_OVERLAP = "duplicate_overlap"
    IMPLAUSIBLE_SIZE = "implausible_size"
    IMPLAUSIBLE_SHAPE = "implausible_shape"
    IMPLAUSIBLE_DISPLACEMENT = "implausible_displacement"
    UNSUPPORTED_TRACK = "unsupported_track"
    STATIC_SCENE = "static_scene"
    OVER_MAX_HANDS = "over_max_hands"


class FilterName(StrEnum):
    DUPLICATE_MERGE = "duplicate_merge"
    SIZE_GATE = "size_gate"
    SHAPE_GATE = "shape_gate"
    BYTE_TRACK = "byte_track"
    DISPLACEMENT_GATE = "displacement_gate"
    TRACK_SUPPORT_GATE = "track_support_gate"
    STATIC_SCENE_GATE = "static_scene_gate"
    MAX_TWO_SELECTOR = "max_two_selector"


class PipelinePhase(StrEnum):
    LOAD = "load"
    COLUMNAR = "columnar"
    GEOMETRIC = "geometric"
    TRACKING = "tracking"
    TEMPORAL = "temporal"
    SELECTION = "selection"
    ARTIFACTS = "artifacts"
    EVALUATION = "evaluation"
    REPORT = "report"
    REGRESSION = "regression"


class RunState(StrEnum):
    CREATED = "created"
    DATASET_SCANNED = "dataset_scanned"
    CLIPS_RUNNING = "clips_running"
    ARTIFACTS_WRITTEN = "artifacts_written"
    EVALUATED = "evaluated"
    REPORTED = "reported"
    REGRESSION_CHECKED = "regression_checked"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunEvent(StrEnum):
    SCAN_OK = "scan_ok"
    CLIP_STARTED = "clip_started"
    CLIP_SUCCEEDED = "clip_succeeded"
    CLIP_FAILED = "clip_failed"
    ALL_CLIPS_SUCCEEDED = "all_clips_succeeded"
    EVAL_SUCCEEDED = "eval_succeeded"
    REPORT_SUCCEEDED = "report_succeeded"
    REGRESSION_SUCCEEDED = "regression_succeeded"
    FAILURE_SEEN = "failure_seen"
    CANCEL_REQUESTED = "cancel_requested"
