from __future__ import annotations

PACKAGE_ID = "handdetect_quality_adapter"
WORKSPACE_ID = "handdetect_quality_story"
DEFAULT_LAYOUT_ID = "handdetect_customer_demo_console"
RAW_OVERLAY_FILE = "raw_overlay.mp4"
ADAPTER_OVERLAY_FILE = "adapter_overlay.mp4"
REJECTED_OVERLAY_FILE = "rejected_overlay.mp4"
COMPARE_OVERLAY_FILE = "compare_raw_adapter.mp4"
THUMBNAIL_STRIP_FILE = "thumbnail_strip.webp"
BOX_INDEX_FILE = "boxes.json"

REASON_LABELS = {
    "duplicate_overlap": "Duplicate Detections",
    "implausible_size": "Implausible Size",
    "implausible_shape": "Implausible Shape",
    "implausible_displacement": "Implausible Motion",
    "unsupported_track": "Unsupported Detection",
    "static_scene": "Static Scene Detection",
    "over_max_hands": "Max-Two Selection",
}

SUPPORT_ROWS = (
    (
        "duplicate_boxes_on_one_hand",
        "Duplicate boxes on one hand",
        "implemented_rejection",
        "Merged or rejected by overlap.",
    ),
    (
        "implausible_size",
        "Implausible size",
        "implemented_rejection",
        "Rejected by vectorized box area gate.",
    ),
    (
        "implausible_shape",
        "Implausible shape",
        "implemented_rejection",
        "Rejected by aspect-ratio gate.",
    ),
    (
        "implausible_displacement",
        "Implausible displacement",
        "implemented_rejection",
        "Rejected by temporal motion gate.",
    ),
    (
        "unsupported_detection",
        "Unsupported detection",
        "implemented_rejection",
        "Rejected when MOT support is too short.",
    ),
    (
        "static_detection",
        "Static detection",
        "implemented_rejection",
        "Rejected when static under camera motion.",
    ),
    (
        "max_two_selection",
        "Max-two selection",
        "implemented_rejection",
        "Only the top two wearer-hand candidates survive per frame.",
    ),
    (
        "hand_exit_side_border",
        "Hand exit side border",
        "heuristic_candidate",
        "Surfaced for review, not scored as correctness.",
    ),
    (
        "brief_occlusion_candidate",
        "Brief occlusion",
        "heuristic_candidate",
        "MOT continuity evidence only in Phase 1.",
    ),
    (
        "possible_bystander_hand",
        "Possible bystander hand",
        "not_supported",
        "Needs calibrated depth or labels.",
    ),
    (
        "false_negative_interpolation",
        "False-negative interpolation",
        "not_supported",
        "Out of scope; count remains zero.",
    ),
)

PLATFORM_LABELS = {
    "report": "Static Report",
    "biodock": "BioDock Berg10",
    "mlflow": "MLflow",
    "dvc": "DVC/DVCLive",
    "evidently": "Evidently",
    "fiftyone": "FiftyOne",
    "label_studio": "Label Studio",
    "cvat": "CVAT",
    "datumaro": "Datumaro",
    "rerun": "Rerun",
}
