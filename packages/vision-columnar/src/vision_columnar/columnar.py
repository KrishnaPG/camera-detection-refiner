from __future__ import annotations

import numpy as np
from handdetect_io.parsers import ValidatedClipBundle

from vision_columnar.blocks import DetectionBlock


class ClipColumnBuilder:
    """Build zero-copy-ready columnar detection tensors from validated clip bundles."""

    def build(self, bundle: ValidatedClipBundle) -> DetectionBlock:
        rows = _collect_rows(bundle)
        if not rows:
            return DetectionBlock(
                clip_id=bundle.paths.clip_id,
                detection_ids=(),
                frame_index=np.empty(0, dtype=np.int32),
                xyxy=np.empty((0, 4), dtype=np.float32),
                confidence=np.empty(0, dtype=np.float32),
                class_id=np.empty(0, dtype=np.int32),
                handedness=(),
                timestamp_ns=np.empty(0, dtype=np.int64),
            )

        frame_index = np.fromiter((row[1] for row in rows), dtype=np.int32, count=len(rows))
        xyxy = np.asarray([row[2:6] for row in rows], dtype=np.float32)
        confidence = np.fromiter((row[6] for row in rows), dtype=np.float32, count=len(rows))
        class_id = np.fromiter((row[7] for row in rows), dtype=np.int32, count=len(rows))
        timestamp_ns = np.fromiter((row[9] for row in rows), dtype=np.int64, count=len(rows))

        return DetectionBlock(
            clip_id=bundle.paths.clip_id,
            detection_ids=tuple(row[0] for row in rows),
            frame_index=frame_index,
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
            handedness=tuple(row[8] for row in rows),
            timestamp_ns=timestamp_ns,
        )


def _collect_rows(
    bundle: ValidatedClipBundle,
) -> list[tuple[str, int, float, float, float, float, float, int, str, int]]:
    rows: list[tuple[str, int, float, float, float, float, float, int, str, int]] = []
    for frame_payload in bundle.hand_boxes.frames:
        frame = int(frame_payload.frame)
        for ordinal, detection in enumerate(frame_payload.detections):
            timestamp = int(bundle.frame_ts.frame_ts[str(frame)])
            rows.append(
                (
                    f"{bundle.paths.clip_id}:{frame}:{ordinal}",
                    frame,
                    float(detection.xyxy[0]),
                    float(detection.xyxy[1]),
                    float(detection.xyxy[2]),
                    float(detection.xyxy[3]),
                    float(detection.confidence),
                    int(detection.class_id),
                    detection.handedness,
                    timestamp,
                ),
            )
    rows.sort(key=lambda row: (row[1], -row[6]))
    return rows
