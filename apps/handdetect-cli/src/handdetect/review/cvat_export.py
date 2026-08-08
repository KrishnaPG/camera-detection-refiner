from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from handdetect.labels.freeze import LabelSetFreezer
from pydantic import BaseModel, ConfigDict, Field

CVAT_TASK_TITLE_MAX_LENGTH = 128
CVAT_DECISION_LABELS = {
    "kept": "adapter_approved",
    "merged": "duplicate_detections",
}
CVAT_STAGE_LABELS = {
    "shape_gate": "implausible_detection",
    "max_two_selector": "adapter_rejected",
    "track_length_gate": "unsupported_detection",
    "motion_gate": "implausible_detection",
}
CVAT_REASON_LABELS = {
    "duplicate_overlap": "duplicate_detections",
    "implausible_shape": "implausible_detection",
    "implausible_size": "implausible_detection",
    "short_track": "unsupported_detection",
    "excessive_motion": "implausible_detection",
}
CVAT_LABEL_COLORS = {
    "adapter_approved": "#30d158",
    "adapter_rejected": "#ff453a",
    "duplicate_detections": "#ffd60a",
    "implausible_detection": "#ff7a45",
    "unsupported_detection": "#8d98a5",
}


JsonMap = dict[str, object]
JsonRows = list[JsonMap]


class CvatHandoffResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    path: Path
    url: str | None
    message: str
    imported_task_count: int
    task_id: int | None = None
    job_ids: tuple[int, ...] = ()
    job_urls: tuple[str, ...] = ()


class CvatCorrectionShape(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int | None
    frame_index: int = Field(ge=0)
    clip_id: str
    frame: int = Field(ge=0)
    label_id: int = Field(ge=0)
    label: str
    type: str
    points: tuple[float, ...]
    occluded: bool
    outside: bool
    source: str
    z_order: int
    attributes: tuple[JsonMap, ...] = ()


class CvatCorrectionFrame(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    clip_id: str
    frame: int = Field(ge=0)
    image_path: Path
    shapes: tuple[CvatCorrectionShape, ...]


class CvatCorrectionImportResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    path: Path
    message: str
    task_id: int | None = None
    job_ids: tuple[int, ...] = ()
    label_set_id: str | None = None
    annotation_sha256: str | None = None
    shape_count: int = 0
    frozen_manifest_path: Path | None = None


class CvatPublisherConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    internal_url: str = ""
    public_url: str = ""
    username: str = ""
    password: str = ""


class CvatCorrectionImporter:
    def import_corrections(
        self,
        run_root: Path,
        config: CvatPublisherConfig,
    ) -> CvatCorrectionImportResult:
        review_root = run_root / "review"
        output = review_root / "cvat-corrections.json"
        freeze_status = review_root / "cvat-label-freeze.json"
        import_manifest = review_root / "cvat-import.json"
        if not self._is_configured(config):
            message = "CVAT correction import skipped because CVAT is not configured"
            self._write_status(output, run_root, "not_configured", message)
            return CvatCorrectionImportResult(status="not_configured", path=output, message=message)
        if not import_manifest.exists():
            message = "CVAT correction import skipped because no CVAT task exists for this run"
            self._write_status(output, run_root, "not_published", message)
            return CvatCorrectionImportResult(status="not_published", path=output, message=message)

        import_payload = _read_json(import_manifest)
        task_id = _optional_int(import_payload.get("task_id"))
        if task_id is None:
            message = "CVAT correction import skipped because cvat-import.json has no task_id"
            self._write_status(output, run_root, "invalid_handoff", message)
            return CvatCorrectionImportResult(
                status="invalid_handoff",
                path=output,
                message=message,
            )

        try:
            payload = self._import_payload(run_root, config, task_id, import_payload)
        except Exception as exc:
            message = f"CVAT correction import fallback: {exc}"
            self._write_status(output, run_root, "import_failed", message, task_id=task_id)
            return CvatCorrectionImportResult(
                status="import_failed",
                path=output,
                message=message,
                task_id=task_id,
                job_ids=_int_tuple(import_payload.get("job_ids")),
            )

        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        annotation_sha256 = hashlib.sha256(canonical).hexdigest()
        payload["annotation_sha256"] = annotation_sha256
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        frozen_manifest = LabelSetFreezer().freeze_tasks(
            output,
            run_root / "labels" / "versions",
            metadata={
                "tool": "cvat",
                "task_id": task_id,
                "job_ids": list(_int_tuple(import_payload.get("job_ids"))),
                "run_suite_id": run_root.parent.name,
                "run_id": run_root.name,
            },
        )
        frozen_payload = _read_json(frozen_manifest)
        label_set_id = _string_value(frozen_payload.get("label_set_id"))
        freeze_payload = {
            "tool": "cvat",
            "handoff_type": "annotation_correction_freeze",
            "status": "ready",
            "task_id": task_id,
            "job_ids": list(_int_tuple(import_payload.get("job_ids"))),
            "label_set_id": label_set_id,
            "annotation_sha256": annotation_sha256,
            "source": _run_relative(run_root, output),
            "manifest_path": _run_relative(run_root, frozen_manifest),
        }
        freeze_status.write_text(json.dumps(freeze_payload, indent=2), encoding="utf-8")
        shape_count = _int_value(payload.get("shape_count"))
        return CvatCorrectionImportResult(
            status="ready",
            path=output,
            message=f"CVAT corrections imported and frozen as label set {label_set_id}",
            task_id=task_id,
            job_ids=_int_tuple(import_payload.get("job_ids")),
            label_set_id=label_set_id,
            annotation_sha256=annotation_sha256,
            shape_count=shape_count,
            frozen_manifest_path=frozen_manifest,
        )

    def _import_payload(
        self,
        run_root: Path,
        config: CvatPublisherConfig,
        task_id: int,
        import_payload: JsonMap,
    ) -> JsonMap:
        from cvat_sdk import make_client  # type: ignore[import-untyped]

        frame_tasks = build_review_frame_tasks(run_root)
        frame_by_index = {task.index: task for task in frame_tasks}
        with make_client(
            config.internal_url, credentials=(config.username, config.password)
        ) as client:
            client.check_server_version(fail_if_unsupported=False)
            task = client.tasks.retrieve(task_id)
            label_rows = _label_rows(task.get_labels())
            label_by_id = {
                _int_value(row.get("id")): _string_value(row.get("name"))
                for row in label_rows
            }
            annotations = task.get_annotations()

        shape_rows = [
            self._shape(shape, frame_by_index, label_by_id)
            for shape in _object_sequence(_attribute_value(annotations, "shapes"))
        ]
        frame_rows = []
        for frame_task in frame_tasks:
            frame_shapes = tuple(
                shape for shape in shape_rows if shape.frame_index == frame_task.index
            )
            frame_rows.append(
                CvatCorrectionFrame(
                    index=frame_task.index,
                    clip_id=frame_task.clip_id,
                    frame=frame_task.frame,
                    image_path=frame_task.image_path,
                    shapes=frame_shapes,
                ).model_dump(mode="json")
            )
        return {
            "tool": "cvat",
            "handoff_type": "annotation_correction_export",
            "status": "ready",
            "task_id": task_id,
            "task_url": import_payload.get("task_url"),
            "job_ids": list(_int_tuple(import_payload.get("job_ids"))),
            "job_urls": list(_string_tuple(import_payload.get("job_urls"))),
            "run_suite_id": run_root.parent.name,
            "run_id": run_root.name,
            "label_schema_hash": _label_schema_hash(label_rows),
            "labels": label_rows,
            "frame_count": len(frame_rows),
            "shape_count": len(shape_rows),
            "frames": frame_rows,
            "media_policy": {
                "copy_state": "not_copied",
                "mode": "zero_copy_absolute_media_references",
            },
        }

    def _shape(
        self,
        shape: object,
        frame_by_index: dict[int, CvatFrameTask],
        label_by_id: dict[int, str],
    ) -> CvatCorrectionShape:
        frame_index = _int_value(_attribute_value(shape, "frame"))
        frame_task = frame_by_index.get(frame_index)
        if frame_task is None:
            raise ValueError(f"CVAT annotation references unknown frame index {frame_index}")
        label_id = _int_value(_attribute_value(shape, "label_id"))
        return CvatCorrectionShape(
            id=_optional_int(_attribute_value(shape, "id")),
            frame_index=frame_index,
            clip_id=frame_task.clip_id,
            frame=frame_task.frame,
            label_id=label_id,
            label=label_by_id.get(label_id, f"label_{label_id}"),
            type=_string_value(_attribute_value(shape, "type")),
            points=tuple(
                _float_value(point)
                for point in _object_sequence(_attribute_value(shape, "points"))
            ),
            occluded=_bool_value(_attribute_value(shape, "occluded")),
            outside=_bool_value(_attribute_value(shape, "outside")),
            source=_string_value(_attribute_value(shape, "source")),
            z_order=_int_value(_attribute_value(shape, "z_order")),
            attributes=_attribute_rows(_attribute_value(shape, "attributes")),
        )

    def _write_status(
        self,
        output: Path,
        run_root: Path,
        status: str,
        message: str,
        *,
        task_id: int | None = None,
    ) -> None:
        payload = {
            "tool": "cvat",
            "handoff_type": "annotation_correction_export",
            "status": status,
            "message": message,
            "run_suite_id": run_root.parent.name,
            "run_id": run_root.name,
            "task_id": task_id,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _is_configured(self, config: CvatPublisherConfig) -> bool:
        return all(
            value.strip()
            for value in [
                config.internal_url,
                config.public_url,
                config.username,
                config.password,
            ]
        )


class CvatHandoffExporter:
    def export(self, run_root: Path, config: CvatPublisherConfig) -> CvatHandoffResult:
        review_root = run_root / "review"
        tasks_path = review_root / "labelstudio-tasks.json"
        output = review_root / "cvat-handoff.json"
        imported_count = self._task_count(tasks_path)
        public_url = config.public_url.rstrip("/") if config.public_url else ""
        payload = self._handoff_payload(run_root, imported_count, "handoff_file")

        if not self._is_configured(config):
            message = (
                "CVAT handoff manifest written; configure HANDDETECT_CVAT_URL, "
                "HANDDETECT_CVAT_PUBLIC_URL, HANDDETECT_CVAT_USERNAME, and "
                "HANDDETECT_CVAT_PASSWORD to create tasks automatically"
            )
            payload.update({"status": "handoff_file", "message": message})
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return CvatHandoffResult(
                status="handoff_file",
                path=output,
                url=public_url or None,
                message=message,
                imported_task_count=imported_count,
            )

        existing = review_root / "cvat-import.json"
        if existing.exists():
            existing_payload = _read_json(existing)
            task_id = _optional_int(existing_payload.get("task_id"))
            job_urls = _string_tuple(existing_payload.get("job_urls"))
            task_url = _string_value(existing_payload.get("task_url")) or (
                f"{public_url}/tasks/{task_id}" if public_url and task_id is not None else None
            )
            primary_url = job_urls[0] if job_urls else task_url
            message = "CVAT task already exists for this immutable run"
            payload.update(
                {
                    "status": "ready",
                    "message": message,
                    "task_id": task_id,
                    "task_url": task_url,
                    "job_urls": list(job_urls),
                }
            )
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return CvatHandoffResult(
                status="ready",
                path=existing,
                url=primary_url,
                message=message,
                imported_task_count=imported_count,
                task_id=task_id,
                job_ids=_int_tuple(existing_payload.get("job_ids")),
                job_urls=job_urls,
            )

        try:
            result = self._publish(run_root, config)
        except Exception as exc:
            message = f"CVAT export fallback: {exc}"
            payload.update({"status": "handoff_ready", "message": message})
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return CvatHandoffResult(
                status="handoff_ready",
                path=output,
                url=public_url or None,
                message=message,
                imported_task_count=imported_count,
            )

        payload.update(
            {
                "status": "ready",
                "message": result.message,
                "task_id": result.task_id,
                "task_url": result.url,
                "job_urls": list(result.job_urls),
            }
        )
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return result

    def _publish(self, run_root: Path, config: CvatPublisherConfig) -> CvatHandoffResult:
        from cvat_sdk import make_client
        from cvat_sdk.api_client import models  # type: ignore[import-untyped]
        from cvat_sdk.core.proxies.tasks import ResourceType  # type: ignore[import-untyped]

        review_root = run_root / "review"
        import_path = review_root / "cvat-import.json"
        frame_tasks = _frame_tasks(run_root)
        image_paths = _materialize_task_images(run_root, frame_tasks)
        labels = _cvat_label_specs(frame_tasks)
        task_name = _cvat_task_name(run_root)
        with make_client(
            config.internal_url, credentials=(config.username, config.password)
        ) as client:
            client.check_server_version(fail_if_unsupported=False)
            task = client.tasks.create_from_data(
                spec={"name": task_name, "labels": labels},
                resources=[str(path) for path in image_paths],
                resource_type=ResourceType.LOCAL,
                data_params={"image_quality": 95},
            )
            label_ids = {str(label.name): int(label.id) for label in task.get_labels()}
            shapes = [
                models.LabeledShapeRequest(
                    type="rectangle",
                    label_id=label_ids[box.label],
                    frame=frame_task.index,
                    occluded=False,
                    outside=False,
                    z_order=0,
                    rotation=0.0,
                    points=[box.x1, box.y1, box.x2, box.y2],
                    source="auto",
                )
                for frame_task in frame_tasks
                for box in frame_task.boxes
                if box.label in label_ids
            ]
            task.set_annotations(
                models.LabeledDataRequest(version=0, tags=[], shapes=shapes, tracks=[])
            )
            jobs = task.get_jobs()

        public_url = config.public_url.rstrip("/")
        job_ids = tuple(int(job.id) for job in jobs)
        job_urls = tuple(f"{public_url}/tasks/{int(task.id)}/jobs/{job_id}" for job_id in job_ids)
        task_url = f"{public_url}/tasks/{int(task.id)}"
        payload = {
            "status": "ready",
            "task_id": int(task.id),
            "task_url": task_url,
            "job_ids": list(job_ids),
            "job_urls": list(job_urls),
            "image_count": len(image_paths),
            "shape_count": len(shapes),
            "label_names": [spec["name"] for spec in labels],
        }
        import_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return CvatHandoffResult(
            status="ready",
            path=import_path,
            url=job_urls[0] if job_urls else task_url,
            message=f"CVAT task created with {len(image_paths)} images and {len(shapes)} boxes",
            imported_task_count=len(image_paths),
            task_id=int(task.id),
            job_ids=job_ids,
            job_urls=job_urls,
        )

    def _task_count(self, tasks_path: Path) -> int:
        if not tasks_path.exists():
            return 0
        parsed = json.loads(tasks_path.read_text(encoding="utf-8"))
        if isinstance(parsed, list):
            return len(parsed)
        return 0

    def _handoff_payload(self, run_root: Path, imported_count: int, status: str) -> JsonMap:
        return {
            "tool": "cvat",
            "handoff_type": "annotation_review",
            "status": status,
            "source_tasks_path": "review/labelstudio-tasks.json",
            "run_suite_id": run_root.parent.name,
            "run_id": run_root.name,
            "label_schema": {"labels": _cvat_label_specs(())},
            "task_count": imported_count,
            "review_artifacts": {
                "story": "review/story.json",
                "platforms": "review/platforms.json",
                "clips": "review/clips/*",
            },
        }

    def _is_configured(self, config: CvatPublisherConfig) -> bool:
        return all(
            value.strip()
            for value in [
                config.internal_url,
                config.public_url,
                config.username,
                config.password,
            ]
        )


class CvatBox(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    x1: float
    y1: float
    x2: float
    y2: float


class CvatFrameTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    clip_id: str
    frame: int = Field(ge=0)
    image_path: Path
    boxes: tuple[CvatBox, ...]


def build_review_frame_tasks(run_root: Path) -> tuple[CvatFrameTask, ...]:
    return _frame_tasks(run_root)


def _frame_tasks(run_root: Path) -> tuple[CvatFrameTask, ...]:
    label_tasks = _read_label_tasks(run_root / "review" / "labelstudio-tasks.json")
    frame_tasks = []
    for index, task in enumerate(label_tasks):
        data = _mapping_value(task.get("data"))
        clip_id = _string_value(data.get("clip_id"))
        frame = _int_value(data.get("frame"))
        image_path = _local_image_path(run_root, _string_value(data.get("image")))
        boxes = _boxes_for_frame(run_root, clip_id, frame)
        frame_tasks.append(
            CvatFrameTask(
                index=index,
                clip_id=clip_id,
                frame=frame,
                image_path=image_path,
                boxes=boxes,
            )
        )
    return tuple(frame_tasks)


def _materialize_task_images(
    run_root: Path, frame_tasks: tuple[CvatFrameTask, ...]
) -> tuple[Path, ...]:
    image_root = run_root / "review" / "cvat-import" / "images"
    image_root.mkdir(parents=True, exist_ok=True)
    output = []
    for task in frame_tasks:
        suffix = task.image_path.suffix or ".png"
        target = image_root / f"{task.index:06d}_{task.clip_id}_{task.frame:06d}{suffix}"
        if not target.exists():
            shutil.copy2(task.image_path, target)
        output.append(target)
    return tuple(output)


def _cvat_label_specs(frame_tasks: tuple[CvatFrameTask, ...]) -> list[JsonMap]:
    labels = set(CVAT_LABEL_COLORS)
    for task in frame_tasks:
        labels.update(box.label for box in task.boxes)
    return [
        {"name": label, "color": CVAT_LABEL_COLORS.get(label, "#2f7dff"), "attributes": []}
        for label in sorted(labels)
    ]


def _boxes_for_frame(run_root: Path, clip_id: str, frame: int) -> tuple[CvatBox, ...]:
    boxes_path = run_root / "review" / "clips" / clip_id / "boxes.json"
    boxes_payload = _read_json(boxes_path)
    frames = boxes_payload.get("frames")
    if not isinstance(frames, list):
        return ()
    for row in frames:
        frame_row = _mapping_value(row)
        if _int_value(frame_row.get("frame"), -1) == frame:
            return tuple(
                _cvat_box(_mapping_value(box)) for box in _list_value(frame_row.get("boxes"))
            )
    return ()


def _cvat_box(row: JsonMap) -> CvatBox:
    return CvatBox(
        label=_box_label(row),
        x1=_float_value(row.get("x1")),
        y1=_float_value(row.get("y1")),
        x2=_float_value(row.get("x2")),
        y2=_float_value(row.get("y2")),
    )


def _box_label(row: JsonMap) -> str:
    reason = _string_value(row.get("reason"))
    if reason in CVAT_REASON_LABELS:
        return CVAT_REASON_LABELS[reason]
    decision = _string_value(row.get("decision"))
    if decision in CVAT_DECISION_LABELS:
        return CVAT_DECISION_LABELS[decision]
    stage = _string_value(row.get("stage"))
    if stage in CVAT_STAGE_LABELS:
        return CVAT_STAGE_LABELS[stage]
    return "adapter_rejected" if decision == "rejected" else "adapter_approved"


def _local_image_path(run_root: Path, image_url: str) -> Path:
    parsed = urlparse(image_url)
    image_name = Path(parsed.path).name
    if not image_name:
        raise ValueError(f"CVAT image URL does not contain a file name: {image_url}")
    target = (run_root / "report" / "samples" / image_name).resolve()
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"CVAT review image not found: {target}")
    if run_root.resolve() not in target.parents:
        raise ValueError(f"CVAT review image escapes run root: {target}")
    return target


def _cvat_task_name(run_root: Path) -> str:
    run_ref = f"{run_root.parent.name}-{run_root.name}"
    digest = hashlib.sha256(run_ref.encode("utf-8")).hexdigest()[:12]
    prefix = f"handdetect-{digest}-"
    suffix_budget = CVAT_TASK_TITLE_MAX_LENGTH - len(prefix)
    return f"{prefix}{run_ref[-suffix_budget:]}"


def _read_label_tasks(path: Path) -> JsonRows:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, list):
        raise ValueError(f"Expected Label Studio task list: {path}")
    return [_mapping_value(row) for row in parsed]


def _read_json(path: Path) -> JsonMap:
    return cast(JsonMap, json.loads(path.read_text(encoding="utf-8")))


def _label_rows(labels: object) -> JsonRows:
    rows = [
        {
            "id": _int_value(_attribute_value(label, "id")),
            "name": _string_value(_attribute_value(label, "name")),
            "color": _string_value(_attribute_value(label, "color")),
        }
        for label in _object_sequence(labels)
    ]
    return sorted(rows, key=lambda row: (_int_value(row.get("id")), _string_value(row.get("name"))))


def _label_schema_hash(labels: JsonRows) -> str:
    payload = json.dumps(labels, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _mapping_value(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _list_value(value: object) -> JsonRows:
    if not isinstance(value, list):
        return []
    return [_mapping_value(row) for row in value]


def _string_value(value: object) -> str:
    return str(value) if value is not None else ""


def _int_value(value: object, fallback: int = 0) -> int:
    try:
        if isinstance(value, int | float | str | bytes | bytearray):
            return int(value)
        return fallback
    except (TypeError, ValueError):
        return fallback


def _optional_int(value: object) -> int | None:
    parsed = _int_value(value, -1)
    return parsed if parsed >= 0 else None


def _int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(_int_value(item) for item in value)


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value)


def _attribute_rows(value: object) -> tuple[JsonMap, ...]:
    return tuple(_mapping_value(row) for row in _object_sequence(value))


def _object_sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, list | tuple):
        return tuple(value)
    return ()


def _attribute_value(value: object, attribute: str) -> object:
    return getattr(value, attribute, None)


def _bool_value(value: object) -> bool:
    return bool(value) if value is not None else False


def _float_value(value: object) -> float:
    try:
        if isinstance(value, int | float | str | bytes | bytearray):
            return float(value)
        return 0.0
    except (TypeError, ValueError):
        return 0.0


def _run_relative(run_root: Path, path: Path) -> str:
    return str(path.relative_to(run_root))
