from __future__ import annotations

import json

import pyarrow as pa
import pyarrow.parquet as pq
from dq_contracts.ids import RunId
from dq_contracts.models import ValidatedClipPathSet
from handdetect.audit.ledger import DecisionLedgerBuilder
from handdetect.filters.geometric import GeometricFilterPipeline
from handdetect.filters.temporal import TemporalFilterPipeline
from handdetect.hotpath.columnar import ClipColumnBuilder
from handdetect.io.parsers import JsonBoundaryParser
from handdetect.runs.manifest import ClipRunSummary
from handdetect.runs.store import RunArtifactStore
from handdetect.selection.max_two import MaxTwoSelector
from handdetect.tracking.bytetrack import ByteTrackAssociationAdapter
from handdetect_domain.config import ExperimentConfig


class ClipRunner:
    def run_clip(
        self,
        paths: ValidatedClipPathSet,
        run_id: RunId,
        experiment: ExperimentConfig,
        store: RunArtifactStore,
    ) -> ClipRunSummary:
        bundle = JsonBoundaryParser().parse_clip(paths)
        block = ClipColumnBuilder().build(bundle)
        geometric = GeometricFilterPipeline().run(block, experiment.adapter)
        tracks = ByteTrackAssociationAdapter().associate(block, geometric, experiment.bytetrack)
        temporal = TemporalFilterPipeline().run(block, tracks, experiment.adapter)
        selected = MaxTwoSelector().select(block, tracks, temporal)
        decisions = DecisionLedgerBuilder().build(run_id, block, geometric, temporal, selected)
        clip_summary = self._write_artifacts(
            paths, run_id, block, tracks, temporal, selected, decisions, store
        )
        return clip_summary

    def _write_artifacts(
        self,
        paths: ValidatedClipPathSet,
        run_id: RunId,
        block: object,
        tracks: object,
        temporal: object,
        selected: object,
        decisions: tuple[object, ...],
        store: RunArtifactStore,
    ) -> ClipRunSummary:
        detection_block = block
        track_block = tracks
        temporal_block = temporal
        selected_block = selected
        cleaned_path = store.cleaned_dir / f"{paths.clip_id}.json"
        audit_path = store.audit_dir / f"{paths.clip_id}.jsonl"
        selected_mask = selected_block.selected_mask
        max_per_frame = self._max_selected_per_frame(detection_block.frame_index, selected_mask)
        payload = {
            "run_id": str(run_id),
            "clip_id": str(paths.clip_id),
            "interpolated_detection_count": 0,
            "max_detections_per_frame": max_per_frame,
            "selected_detection_count": int(selected_mask.sum()),
            "detections": [
                {
                    "detection_id": detection_block.detection_ids[index],
                    "frame": int(detection_block.frame_index[index]),
                    "selected": bool(selected_mask[index]),
                    "track_id": (
                        int(selected_block.track_id[index])
                        if int(selected_block.track_id[index]) >= 0
                        else None
                    ),
                }
                for index in range(detection_block.detection_count)
            ],
        }
        cleaned_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        audit_path.write_text(
            "\n".join(record.model_dump_json() for record in decisions),
            encoding="utf-8",
        )
        self._write_parquet_tables(
            paths, detection_block, track_block, temporal_block, selected_block, decisions, store
        )
        return ClipRunSummary(
            run_id=str(run_id),
            clip_id=str(paths.clip_id),
            interpolated_detection_count=0,
            max_detections_per_frame=max_per_frame,
            selected_detection_count=int(selected_mask.sum()),
            raw_detection_count=detection_block.detection_count,
            rejected_detection_count=int(
                detection_block.detection_count - int(selected_mask.sum())
            ),
        )

    def _max_selected_per_frame(self, frame_index: object, selected_mask: object) -> int:
        max_selected = 0
        for frame in set(frame_index.tolist()):
            count = int(selected_mask[frame_index == frame].sum())
            max_selected = max(max_selected, count)
        return max_selected

    def _write_parquet_tables(
        self,
        paths: ValidatedClipPathSet,
        block: object,
        tracks: object,
        temporal: object,
        selected: object,
        decisions: tuple[object, ...],
        store: RunArtifactStore,
    ) -> None:
        detections = pa.table(
            {
                "clip_id": [str(paths.clip_id)] * block.detection_count,
                "detection_id": list(block.detection_ids),
                "frame_index": block.frame_index,
                "x1": block.xyxy[:, 0],
                "y1": block.xyxy[:, 1],
                "x2": block.xyxy[:, 2],
                "y2": block.xyxy[:, 3],
                "confidence": block.confidence,
                "selected": selected.selected_mask,
                "selected_track_id": selected.track_id,
            }
        )
        tracks_table = pa.table(
            {
                "clip_id": [str(paths.clip_id)] * len(tracks.source_detection_index),
                "source_detection_index": tracks.source_detection_index,
                "track_id": tracks.track_id,
                "track_age_frames": tracks.track_age_frames,
                "track_score": tracks.track_score,
                "kept_after_temporal": temporal.keep_mask,
            }
        )
        decisions_table = pa.table(
            {
                "clip_id": [str(record.clip_id) for record in decisions],
                "detection_id": [str(record.detection_id) for record in decisions],
                "decision": [record.decision.value for record in decisions],
                "stage": [record.stage.value for record in decisions],
                "reason": [
                    record.reason.value if record.reason is not None else "" for record in decisions
                ],
            }
        )
        clip_metrics = pa.table(
            {
                "clip_id": [str(paths.clip_id)],
                "raw_detection_count": [block.detection_count],
                "selected_detection_count": [int(selected.selected_mask.sum())],
                "rejected_detection_count": [
                    int(block.detection_count - int(selected.selected_mask.sum()))
                ],
                "interpolated_detection_count": [0],
            }
        )
        pq.write_table(detections, store.tables_dir / f"detections_{paths.clip_id}.parquet")
        pq.write_table(tracks_table, store.tables_dir / f"tracks_{paths.clip_id}.parquet")
        pq.write_table(decisions_table, store.tables_dir / f"decisions_{paths.clip_id}.parquet")
        self._append_or_write(clip_metrics, store.tables_dir / "clip_metrics.parquet")

    def _append_or_write(self, table: pa.Table, path: object) -> None:
        table_path = path
        if table_path.exists():
            existing = pq.read_table(table_path)
            table = pa.concat_tables([existing, table], promote_options="default")
        pq.write_table(table, table_path)
