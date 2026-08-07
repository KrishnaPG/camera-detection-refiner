from __future__ import annotations

import json
from pathlib import Path

import cv2


class OverlaySampler:
    def write_contact_sheet(self, run_root: Path) -> Path:
        sample_dir = run_root / "report" / "samples"
        sample_dir.mkdir(parents=True, exist_ok=True)
        manifest = json.loads(
            (run_root / "report" / "sample-manifest.json").read_text(encoding="utf-8")
        )
        run_manifest = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
        data_root = Path(run_manifest["data_root"])
        fragments: list[str] = ["<!doctype html><html><body><h1>Contact Sheet</h1>"]
        for sample in manifest["samples"]:
            image_path = sample_dir / sample["image_name"]
            self._write_sample_image(data_root, sample["clip_id"], int(sample["frame"]), image_path)
            fragments.append(
                f'<figure><img src="samples/{image_path.name}" width="480" />'
                f"<figcaption>{sample['clip_id']} frame {sample['frame']}</figcaption></figure>",
            )
        fragments.append("</body></html>\n")
        output = run_root / "report" / "contact-sheet.html"
        output.write_text("".join(fragments), encoding="utf-8")
        return output

    def _write_sample_image(
        self, data_root: Path, clip_id: str, frame_index: int, output: Path
    ) -> None:
        clip_video = data_root / clip_id / "video_left.mp4"
        capture = cv2.VideoCapture(str(clip_video))
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        capture.release()
        if not ok or frame is None:
            placeholder = 255 * cv2.UMat(240, 480, cv2.CV_8UC3).get()
            cv2.putText(
                placeholder,
                f"{clip_id} frame {frame_index} unavailable",
                (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.imwrite(str(output), placeholder)
            return
        cv2.imwrite(str(output), frame)
