from __future__ import annotations

from pathlib import Path

from dq_contracts.ids import ClipId
from dq_contracts.models import ValidatedClipPathSet


class DatasetScanError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DatasetScanner:
    def scan(self, data_root: Path) -> tuple[ValidatedClipPathSet, ...]:
        if not data_root.exists():
            raise DatasetScanError(f"data root does not exist: {data_root}")

        clips: list[ValidatedClipPathSet] = []
        for clip_dir in sorted(
            path for path in data_root.iterdir() if path.is_dir() and not path.name.startswith(".")
        ):
            clip_id = ClipId(clip_dir.name)
            paths = ValidatedClipPathSet(
                clip_id=clip_id,
                clip_dir=clip_dir,
                meta_path=clip_dir / "meta.json",
                hand_boxes_path=clip_dir / "hand_boxes.json",
                frame_ts_path=clip_dir / "frame_ts.json",
                vio_pose_path=clip_dir / "vio_pose.json",
                video_left_path=clip_dir / "video_left.mp4",
                video_right_path=clip_dir / "video_right.mp4",
            )
            required_paths = [
                paths.meta_path,
                paths.hand_boxes_path,
                paths.frame_ts_path,
                paths.vio_pose_path,
                paths.video_left_path,
                paths.video_right_path,
            ]
            missing = [path.name for path in required_paths if not path.exists()]
            if missing:
                raise DatasetScanError(
                    f"clip {clip_id} missing required files: {missing}",
                )
            clips.append(paths)

        if not clips:
            raise DatasetScanError(f"data root contains no clip directories: {data_root}")

        return tuple(clips)
