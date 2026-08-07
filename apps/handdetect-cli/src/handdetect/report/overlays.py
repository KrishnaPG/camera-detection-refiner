from __future__ import annotations

import json
from collections import Counter
from html import escape
from pathlib import Path

import cv2
import pyarrow.parquet as pq


class OverlaySampler:
    def write_contact_sheet(self, run_root: Path) -> Path:
        sample_dir = run_root / "report" / "samples"
        overlay_dir = run_root / "report" / "overlays"
        sample_dir.mkdir(parents=True, exist_ok=True)
        overlay_dir.mkdir(parents=True, exist_ok=True)
        manifest = json.loads(
            (run_root / "report" / "sample-manifest.json").read_text(encoding="utf-8")
        )
        run_manifest = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
        data_root = Path(run_manifest["data_root"])
        fragments = self._html_header(run_manifest)
        for sample in manifest["samples"]:
            image_path = sample_dir / sample["image_name"]
            self._write_sample_image(data_root, sample["clip_id"], int(sample["frame"]), image_path)
            rows = self._frame_rows(run_root, str(sample["clip_id"]), int(sample["frame"]))
            overlay_paths = self._write_overlays(image_path, overlay_dir, rows)
            fragments.append(self._sample_section(sample, rows, image_path, overlay_paths))
        fragments.append("</main></body></html>\n")
        output = run_root / "report" / "contact-sheet.html"
        html = "".join(fragments)
        output.write_text(html, encoding="utf-8")
        (run_root / "report" / "visual-review.html").write_text(html, encoding="utf-8")
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

    def _frame_rows(
        self, run_root: Path, clip_id: str, frame_index: int
    ) -> list[dict[str, object]]:
        detections_table = pq.read_table(run_root / "tables" / f"detections_{clip_id}.parquet")
        decisions_table = pq.read_table(run_root / "tables" / f"decisions_{clip_id}.parquet")
        tracks_table = pq.read_table(run_root / "tables" / f"tracks_{clip_id}.parquet")
        decisions = {str(row["detection_id"]): row for row in decisions_table.to_pylist()}
        tracks = {
            int(row["source_detection_index"]): row
            for row in tracks_table.to_pylist()
            if "source_detection_index" in row
        }
        rows: list[dict[str, object]] = []
        for source_index, row in enumerate(detections_table.to_pylist()):
            if int(row["frame_index"]) != frame_index:
                continue
            detection_id = str(row["detection_id"])
            decision = decisions.get(detection_id, {})
            track = tracks.get(source_index, {})
            rows.append(
                {
                    **row,
                    "decision": str(decision.get("decision", "unknown")),
                    "stage": str(decision.get("stage", "")),
                    "reason": str(decision.get("reason", "")),
                    "track_id": self._track_id(row, track),
                    "track_age_frames": track.get("track_age_frames"),
                    "track_score": track.get("track_score"),
                }
            )
        return rows

    def _track_id(self, detection: dict[str, object], track: dict[str, object]) -> int | None:
        if "track_id" in track and int(track["track_id"]) >= 0:
            return int(track["track_id"])
        selected_track = int(detection.get("selected_track_id", -1))
        return selected_track if selected_track >= 0 else None

    def _write_overlays(
        self,
        image_path: Path,
        overlay_dir: Path,
        rows: list[dict[str, object]],
    ) -> dict[str, Path]:
        outputs = {
            "raw": overlay_dir / f"{image_path.stem}_raw.png",
            "kept": overlay_dir / f"{image_path.stem}_kept.png",
            "rejected": overlay_dir / f"{image_path.stem}_rejected.png",
        }
        self._draw_overlay(image_path, outputs["raw"], rows, "raw")
        self._draw_overlay(image_path, outputs["kept"], rows, "kept")
        self._draw_overlay(image_path, outputs["rejected"], rows, "rejected")
        return outputs

    def _draw_overlay(
        self,
        image_path: Path,
        output_path: Path,
        rows: list[dict[str, object]],
        mode: str,
    ) -> None:
        frame = cv2.imread(str(image_path))
        if frame is None:
            return
        for row in rows:
            decision = str(row["decision"])
            if mode == "kept" and decision != "kept":
                continue
            if mode == "rejected" and decision == "kept":
                continue
            color = self._box_color(decision)
            x1, y1, x2, y2 = (int(float(row[key])) for key in ("x1", "y1", "x2", "y2"))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 4)
            self._draw_label(frame, x1, y1, self._box_label(row, mode), color)
        cv2.imwrite(str(output_path), frame)

    def _box_color(self, decision: str) -> tuple[int, int, int]:
        if decision == "kept":
            return (40, 180, 80)
        if decision == "merged":
            return (0, 165, 255)
        return (40, 40, 220)

    def _box_label(self, row: dict[str, object], mode: str) -> str:
        confidence = float(row["confidence"])
        track_id = row.get("track_id")
        track_text = f" T{track_id}" if track_id is not None else ""
        if mode == "raw":
            return f"raw {confidence:.2f}{track_text}"
        decision = str(row["decision"])
        stage = str(row.get("stage") or "")
        reason = str(row.get("reason") or "")
        cause = f" {stage}" if stage else ""
        if reason:
            cause = f"{cause}:{reason}"
        return f"{decision}{track_text} {confidence:.2f}{cause}"

    def _draw_label(
        self,
        frame: object,
        x: int,
        y: int,
        label: str,
        color: tuple[int, int, int],
    ) -> None:
        origin = (max(x, 0), max(y - 10, 20))
        size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
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
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    def _html_header(self, run_manifest: dict[str, object]) -> list[str]:
        return [
            '<!doctype html><html lang="en"><head><meta charset="utf-8" />',
            "<title>Visual Review</title>",
            "<style>",
            "body{font-family:system-ui,sans-serif;margin:0;color:#17202a;background:#f7f9fc}",
            "main{max-width:118rem;margin:0 auto;padding:1.5rem}",
            "article{border-top:1px solid #d8dee8;padding:1.25rem 0}",
            ".grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.75rem}",
            "figure{margin:0;background:#fff;border:1px solid #d8dee8;padding:.5rem}",
            "img{width:100%;height:auto;display:block}",
            "figcaption{font-size:.85rem;margin-top:.4rem;color:#334155}",
            "table{border-collapse:collapse;width:100%;background:#fff;margin-top:.75rem}",
            "th,td{border:1px solid #d8dee8;padding:.35rem;text-align:left;font-size:.85rem}",
            ".summary{display:flex;gap:.75rem;flex-wrap:wrap}",
            ".summary code{background:#e8eef7;padding:.15rem .35rem}",
            "</style></head><body><main>",
            "<h1>Visual Review</h1>",
            f"<p>Run <code>{escape(str(run_manifest['run_suite_id']))}/",
            f"{escape(str(run_manifest['run_id']))}</code></p>",
        ]

    def _sample_section(
        self,
        sample: dict[str, object],
        rows: list[dict[str, object]],
        image_path: Path,
        overlay_paths: dict[str, Path],
    ) -> str:
        counts = Counter(str(row["decision"]) for row in rows)
        stage_counts = Counter(self._stage_reason(row) for row in rows if self._stage_reason(row))
        summary = (
            f'<div class="summary"><code>raw {len(rows)}</code>'
            f"<code>kept {counts.get('kept', 0)}</code>"
            f"<code>rejected {counts.get('rejected', 0)}</code>"
            f"<code>merged {counts.get('merged', 0)}</code></div>"
        )
        stages = ", ".join(
            f"{escape(stage)} ({count})" for stage, count in sorted(stage_counts.items())
        )
        table = self._decision_table(rows)
        rejected_figure = self._figure(
            Path("overlays") / overlay_paths["rejected"].name,
            "Rejected or merged",
        )
        return (
            "<article>"
            f"<h2>{escape(str(sample['clip_id']))} frame {int(sample['frame'])}</h2>"
            f"{summary}<p>{escape(stages) if stages else 'No filter stages on this frame.'}</p>"
            '<div class="grid">'
            f"{self._figure(Path('samples') / image_path.name, 'Input frame')}"
            f"{self._figure(Path('overlays') / overlay_paths['raw'].name, 'Raw detections')}"
            f"{self._figure(Path('overlays') / overlay_paths['kept'].name, 'Kept output')}"
            f"{rejected_figure}"
            f"</div>{table}</article>"
        )

    def _figure(self, src: Path, caption: str) -> str:
        return (
            f'<figure><img src="{escape(str(src))}" />'
            f"<figcaption>{escape(caption)}</figcaption></figure>"
        )

    def _stage_reason(self, row: dict[str, object]) -> str:
        stage = str(row.get("stage") or "").strip()
        reason = str(row.get("reason") or "").strip()
        if not reason:
            return stage
        return f"{stage}:{reason}"

    def _decision_table(self, rows: list[dict[str, object]]) -> str:
        body = []
        for row in rows:
            body.append(
                "<tr>"
                f"<td>{escape(str(row['detection_id']))}</td>"
                f"<td>{escape(str(row['decision']))}</td>"
                f"<td>{escape(str(row.get('track_id') or ''))}</td>"
                f"<td>{float(row['confidence']):.3f}</td>"
                f"<td>{escape(self._stage_reason(row))}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>Detection</th><th>Decision</th><th>Track</th>"
            "<th>Confidence</th><th>Stage</th></tr></thead><tbody>"
            + "".join(body)
            + "</tbody></table>"
        )
