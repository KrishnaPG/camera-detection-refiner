from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import cv2
import numpy as np
import pyarrow.parquet as pq  # type: ignore[import-untyped]

JsonMap = dict[str, object]
JsonRows = list[JsonMap]

VIDEO_LEFT_FILE = "video_left.mp4"
RAW_OVERLAY_FILE = "raw_overlay.mp4"
ADAPTER_OVERLAY_FILE = "adapter_overlay.mp4"
REJECTED_OVERLAY_FILE = "rejected_overlay.mp4"
COMPARE_OVERLAY_FILE = "compare_raw_adapter.mp4"
THUMBNAIL_STRIP_FILE = "thumbnail_strip.webp"
BOX_INDEX_FILE = "boxes.json"
THUMBNAIL_HEIGHT = 72
THUMBNAIL_COUNT = 40
REVIEW_MAX_WIDTH = 640
REVIEW_TARGET_FPS = 12.0
FFMPEG_BIN = "ffmpeg"
FFMPEG_LOG_LEVEL = "error"
FFMPEG_PRESET = "veryfast"
FFMPEG_CRF = "28"
FFMPEG_PIX_FMT_IN = "bgr24"
FFMPEG_PIX_FMT_OUT = "yuv420p"
FFMPEG_VIDEO_CODEC = "libx264"
BOX_THICKNESS = 3
LABEL_SCALE = 0.55
LABEL_THICKNESS = 2
KEPT_COLOR = (48, 209, 88)
RAW_COLOR = (47, 125, 255)
REJECTED_COLOR = (58, 69, 255)
MERGED_COLOR = (10, 214, 255)
TEXT_COLOR = (255, 255, 255)


@dataclass(frozen=True, slots=True)
class ClipMediaInput:
    """Purpose: identify one persisted clip that needs review-stage media."""

    run_root: Path
    data_root: Path
    clip_id: str
    frame_count: int
    fps: float


class ReviewMediaArtifactBuilder:
    """Purpose: render browser media from persisted review tables.

    Ownership boundary: this module is the only full-video decode path for story review
    artifacts. It runs after adapter decisions are persisted, never in the adapter hot path.
    """

    def build_clip(self, media: ClipMediaInput) -> None:
        clip_root = media.run_root / "review" / "clips" / media.clip_id
        clip_root.mkdir(parents=True, exist_ok=True)
        detections = _read_rows(media.run_root / "tables" / f"detections_{media.clip_id}.parquet")
        decisions = _read_rows(media.run_root / "tables" / f"decisions_{media.clip_id}.parquet")
        tracks = _read_rows(media.run_root / "tables" / f"tracks_{media.clip_id}.parquet")
        rows_by_frame = _rows_by_frame(detections, decisions, tracks)
        self._render_video_set(media, rows_by_frame)

    def _render_video_set(
        self,
        media: ClipMediaInput,
        rows_by_frame: dict[int, JsonRows],
    ) -> None:
        source = media.data_root / media.clip_id / VIDEO_LEFT_FILE
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            _write_missing_media_placeholders(media, rows_by_frame)
            return
        try:
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(capture.get(cv2.CAP_PROP_FPS)) or media.fps
            _write_box_index(
                media.run_root / "review" / "clips" / media.clip_id / BOX_INDEX_FILE,
                rows_by_frame,
                width,
                height,
            )
            review_size = _review_size(width, height)
            stride = _frame_stride(fps)
            writer_set = _VideoWriterSet.create(
                media.run_root,
                media.clip_id,
                review_size.width,
                review_size.height,
                fps / stride,
            )
            try:
                thumbnails = self._render_frames(
                    media, capture, writer_set, rows_by_frame, review_size, stride
                )
            finally:
                writer_set.release()
            _write_thumbnail_strip(media.run_root, media.clip_id, thumbnails)
        finally:
            capture.release()

    def _render_frames(
        self,
        media: ClipMediaInput,
        capture: cv2.VideoCapture,
        writer_set: _VideoWriterSet,
        rows_by_frame: dict[int, JsonRows],
        review_size: _ReviewSize,
        stride: int,
    ) -> list[np.ndarray]:
        thumbnails: list[np.ndarray] = []
        sample_every = max(media.frame_count // THUMBNAIL_COUNT, 1)
        frame_index = 0
        while frame_index < media.frame_count:
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            if frame_index % stride != 0:
                frame_index += 1
                continue
            review_frame = _resize_review_frame(frame, review_size)
            rows = rows_by_frame.get(frame_index, [])
            raw_frame = _draw_mode(review_frame, rows, "raw", review_size)
            adapter_frame = _draw_mode(review_frame, rows, "adapter", review_size)
            rejected_frame = _draw_mode(review_frame, rows, "rejected", review_size)
            writer_set.write(raw_frame, adapter_frame, rejected_frame)
            if frame_index % sample_every == 0:
                thumbnails.append(_thumbnail(frame))
            frame_index += 1
        return thumbnails


@dataclass(slots=True)
class _VideoWriterSet:
    raw: _FfmpegVideoWriter
    adapter: _FfmpegVideoWriter
    rejected: _FfmpegVideoWriter
    compare: _FfmpegVideoWriter

    @classmethod
    def create(
        cls,
        run_root: Path,
        clip_id: str,
        width: int,
        height: int,
        fps: float,
    ) -> _VideoWriterSet:
        clip_root = run_root / "review" / "clips" / clip_id
        return cls(
            raw=_FfmpegVideoWriter.create(clip_root / RAW_OVERLAY_FILE, width, height, fps),
            adapter=_FfmpegVideoWriter.create(clip_root / ADAPTER_OVERLAY_FILE, width, height, fps),
            rejected=_FfmpegVideoWriter.create(
                clip_root / REJECTED_OVERLAY_FILE, width, height, fps
            ),
            compare=_FfmpegVideoWriter.create(
                clip_root / COMPARE_OVERLAY_FILE, width * 2, height, fps
            ),
        )

    def write(
        self, raw_frame: np.ndarray, adapter_frame: np.ndarray, rejected_frame: np.ndarray
    ) -> None:
        self.raw.write(raw_frame)
        self.adapter.write(adapter_frame)
        self.rejected.write(rejected_frame)
        self.compare.write(np.hstack((raw_frame, adapter_frame)))

    def release(self) -> None:
        self.raw.release()
        self.adapter.release()
        self.rejected.release()
        self.compare.release()


@dataclass(slots=True)
class _FfmpegVideoWriter:
    process: subprocess.Popen[bytes]
    output_path: Path

    @classmethod
    def create(cls, output_path: Path, width: int, height: int, fps: float) -> _FfmpegVideoWriter:
        command = _ffmpeg_command(output_path, width, height, fps)
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        return cls(process=process, output_path=output_path)

    def write(self, frame: np.ndarray) -> None:
        if self.process.stdin is None:
            raise RuntimeError(f"ffmpeg stdin closed for {self.output_path}")
        self.process.stdin.write(frame.tobytes())

    def release(self) -> None:
        if self.process.stdin is not None:
            self.process.stdin.close()
        stderr = self.process.stderr.read() if self.process.stderr is not None else b""
        status = self.process.wait()
        if status != 0:
            message = stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"ffmpeg failed for {self.output_path}: {message}")


@dataclass(frozen=True, slots=True)
class _ReviewSize:
    width: int
    height: int
    scale_x: float
    scale_y: float


def _rows_by_frame(
    detections: JsonRows, decisions: JsonRows, tracks: JsonRows
) -> dict[int, JsonRows]:
    decisions_by_id = {str(row["detection_id"]): row for row in decisions}
    tracks_by_source = {
        int(row["source_detection_index"]): row
        for row in tracks
        if int(row.get("track_id", -1)) >= 0
    }
    grouped: dict[int, JsonRows] = defaultdict(list)
    for source_index, detection in enumerate(detections):
        decision = decisions_by_id.get(str(detection["detection_id"]), {})
        track = tracks_by_source.get(source_index, {})
        row = _box_row(source_index, detection, decision, track)
        grouped[int(detection["frame_index"])].append(row)
    return dict(grouped)


def _ffmpeg_command(output_path: Path, width: int, height: int, fps: float) -> list[str]:
    return [
        FFMPEG_BIN,
        "-hide_banner",
        "-loglevel",
        FFMPEG_LOG_LEVEL,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        FFMPEG_PIX_FMT_IN,
        "-s",
        f"{width}x{height}",
        "-r",
        f"{fps:.3f}",
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        FFMPEG_VIDEO_CODEC,
        "-preset",
        FFMPEG_PRESET,
        "-crf",
        FFMPEG_CRF,
        "-pix_fmt",
        FFMPEG_PIX_FMT_OUT,
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def _box_row(source_index: int, detection: JsonMap, decision: JsonMap, track: JsonMap) -> JsonMap:
    return {
        "source_index": source_index,
        "detection_id": str(detection["detection_id"]),
        "frame": int(detection["frame_index"]),
        "x1": float(detection["x1"]),
        "y1": float(detection["y1"]),
        "x2": float(detection["x2"]),
        "y2": float(detection["y2"]),
        "confidence": float(detection["confidence"]),
        "decision": str(decision.get("decision", "unknown")),
        "stage": str(decision.get("stage", "")),
        "reason": str(decision.get("reason", "")),
        "track_id": _track_id(detection, track),
    }


def _track_id(detection: JsonMap, track: JsonMap) -> int | None:
    if "track_id" in track and int(track["track_id"]) >= 0:
        return int(track["track_id"])
    selected = int(detection.get("selected_track_id", -1))
    return selected if selected >= 0 else None


def _draw_mode(
    frame: np.ndarray, rows: JsonRows, mode: str, review_size: _ReviewSize
) -> np.ndarray:
    output = frame.copy()
    for row in rows:
        decision = str(row["decision"])
        if mode == "adapter" and decision != "kept":
            continue
        if mode == "rejected" and decision == "kept":
            continue
        _draw_box(output, row, _row_color(row, mode), _label(row, mode), review_size)
    return output


def _draw_box(
    frame: np.ndarray,
    row: JsonMap,
    color: tuple[int, int, int],
    label: str,
    review_size: _ReviewSize,
) -> None:
    x1 = int(float(row["x1"]) * review_size.scale_x)
    y1 = int(float(row["y1"]) * review_size.scale_y)
    x2 = int(float(row["x2"]) * review_size.scale_x)
    y2 = int(float(row["y2"]) * review_size.scale_y)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, BOX_THICKNESS)
    origin = (max(x1, 0), max(y1 - 8, 20))
    size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, LABEL_SCALE, LABEL_THICKNESS)
    cv2.rectangle(
        frame,
        (origin[0], origin[1] - size[1] - baseline - 4),
        (origin[0] + size[0] + 8, origin[1] + baseline),
        color,
        -1,
    )
    cv2.putText(
        frame,
        label,
        (origin[0] + 4, origin[1] - 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        LABEL_SCALE,
        TEXT_COLOR,
        LABEL_THICKNESS,
        cv2.LINE_AA,
    )


def _row_color(row: JsonMap, mode: str) -> tuple[int, int, int]:
    if mode == "raw":
        return RAW_COLOR
    decision = str(row["decision"])
    if decision == "kept":
        return KEPT_COLOR
    if decision == "merged":
        return MERGED_COLOR
    return REJECTED_COLOR


def _label(row: JsonMap, mode: str) -> str:
    confidence = float(row["confidence"])
    track = row.get("track_id")
    track_text = f" T{track}" if track is not None else ""
    if mode == "raw":
        return f"det {confidence:.2f}{track_text}"
    decision = str(row["decision"])
    stage = str(row.get("stage") or "")
    reason = str(row.get("reason") or stage)
    return f"{decision}{track_text} {confidence:.2f} {reason}".strip()


def _thumbnail(frame: np.ndarray) -> np.ndarray:
    height, width = frame.shape[:2]
    scaled_width = max(int(width * (THUMBNAIL_HEIGHT / max(height, 1))), 1)
    return cv2.resize(frame, (scaled_width, THUMBNAIL_HEIGHT), interpolation=cv2.INTER_AREA)


def _review_size(width: int, height: int) -> _ReviewSize:
    if width <= REVIEW_MAX_WIDTH:
        return _ReviewSize(width=width, height=height, scale_x=1.0, scale_y=1.0)
    scale = REVIEW_MAX_WIDTH / max(width, 1)
    scaled_height = max(int(height * scale), 1)
    return _ReviewSize(
        width=REVIEW_MAX_WIDTH,
        height=scaled_height,
        scale_x=scale,
        scale_y=scale,
    )


def _resize_review_frame(frame: np.ndarray, review_size: _ReviewSize) -> np.ndarray:
    height, width = frame.shape[:2]
    if width == review_size.width and height == review_size.height:
        return frame
    return cv2.resize(
        frame,
        (review_size.width, review_size.height),
        interpolation=cv2.INTER_AREA,
    )


def _frame_stride(fps: float) -> int:
    return max(round(fps / REVIEW_TARGET_FPS), 1)


def _write_thumbnail_strip(run_root: Path, clip_id: str, thumbnails: list[np.ndarray]) -> None:
    output = run_root / "review" / "clips" / clip_id / THUMBNAIL_STRIP_FILE
    if not thumbnails:
        cv2.imwrite(str(output), np.zeros((THUMBNAIL_HEIGHT, THUMBNAIL_HEIGHT, 3), dtype=np.uint8))
        return
    cv2.imwrite(str(output), np.hstack(thumbnails))


def _write_box_index(
    path: Path,
    rows_by_frame: dict[int, JsonRows],
    video_width: int,
    video_height: int,
) -> None:
    frames = [
        {"frame": frame, "boxes": rows} for frame, rows in sorted(rows_by_frame.items()) if rows
    ]
    payload = {"video_width": video_width, "video_height": video_height, "frames": frames}
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _write_missing_media_placeholders(
    media: ClipMediaInput, rows_by_frame: dict[int, JsonRows]
) -> None:
    frame = np.zeros((240, 426, 3), dtype=np.uint8)
    cv2.putText(
        frame,
        f"{media.clip_id} video unavailable",
        (18, 122),
        cv2.FONT_HERSHEY_SIMPLEX,
        LABEL_SCALE,
        TEXT_COLOR,
        LABEL_THICKNESS,
        cv2.LINE_AA,
    )
    writer_set = _VideoWriterSet.create(media.run_root, media.clip_id, 426, 240, media.fps)
    try:
        for _ in range(max(min(media.frame_count, 30), 1)):
            writer_set.write(frame, frame, frame)
    finally:
        writer_set.release()
    _write_thumbnail_strip(media.run_root, media.clip_id, [_thumbnail(frame)])
    boxes_path = media.run_root / "review" / "clips" / media.clip_id / BOX_INDEX_FILE
    _write_box_index(boxes_path, rows_by_frame, 426, 240)


def _read_rows(path: Path) -> JsonRows:
    return cast(JsonRows, pq.read_table(path).to_pylist())
