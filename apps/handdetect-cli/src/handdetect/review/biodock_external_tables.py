from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol, cast

from handdetect.review.story_constants import PACKAGE_ID
from pydantic import BaseModel, ConfigDict, Field

HANDDETECT_STORY_ROWS_TABLE = "handdetect_story_rows"
HANDDETECT_STORY_ROWS_SOURCE_ID = "external-source:handdetect:story-rows"
HANDDETECT_STORY_ROWS_TABLE_ID = "018f1111-1111-7111-8111-111111111111"
HANDDETECT_STORY_ROWS_LOCATOR = "handdetect/story_rows/*.jsonl"
HANDDETECT_STORY_ROWS_SCHEMA_REF = "schemas/handdetect-story-row.schema.json"
HANDDETECT_STORY_ROWS_SCHEMA_FINGERPRINT = tuple([11] * 32)

JsonMap = dict[str, object]


class BiodockExternalSourceArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    registration_id: str = Field(min_length=1)
    raw_locator: str = Field(min_length=1)
    file_count: int = Field(ge=0)
    byte_length: int = Field(ge=0)
    object_fingerprint: str = Field(min_length=1)


class BiodockExternalTableArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    table_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    relative_pattern: str = Field(min_length=1)
    source_registration_id: str = Field(min_length=1)
    schema_ref: str = Field(min_length=1)
    schema_fingerprint: tuple[int, ...] = Field(min_length=32, max_length=32)


class BiodockExternalTablePublication(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: BiodockExternalSourceArtifact
    table: BiodockExternalTableArtifact
    rows_path: Path
    row_count: int = Field(ge=0)


class BiodockRpcTransport(Protocol):
    async def request(self, method: str, params: dict[str, object]) -> object:
        """Send one JSON-RPC request."""

    async def aclose(self) -> None:
        """Close transport resources."""


class BiodockExternalTableArtifactPublisher:
    """Publish story rows as no-copy Berg10 mounted external-table artifacts."""

    def write_story_rows(
        self,
        run_root: Path,
        external_table_root: Path,
    ) -> BiodockExternalTablePublication:
        story_path = run_root / "review" / "story.json"
        story = _read_json(story_path)
        suite_id = _string(story["run_suite_id"])
        run_id = _string(story["run_id"])
        rows = tuple(_story_rows(run_root, story))
        rows_path = external_table_root / "handdetect" / "story_rows" / _rows_filename(
            suite_id,
            run_id,
        )
        _write_jsonl(rows_path, rows)
        byte_length = rows_path.stat().st_size
        return BiodockExternalTablePublication(
            source=BiodockExternalSourceArtifact(
                byte_length=byte_length,
                file_count=1,
                object_fingerprint=f"sha256:{_sha256_file(rows_path)}",
                raw_locator=HANDDETECT_STORY_ROWS_LOCATOR,
                registration_id=HANDDETECT_STORY_ROWS_SOURCE_ID,
            ),
            table=BiodockExternalTableArtifact(
                display_name=HANDDETECT_STORY_ROWS_TABLE,
                relative_pattern=HANDDETECT_STORY_ROWS_LOCATOR,
                schema_fingerprint=HANDDETECT_STORY_ROWS_SCHEMA_FINGERPRINT,
                schema_ref=HANDDETECT_STORY_ROWS_SCHEMA_REF,
                source_registration_id=HANDDETECT_STORY_ROWS_SOURCE_ID,
                table_id=HANDDETECT_STORY_ROWS_TABLE_ID,
            ),
            rows_path=rows_path,
            row_count=len(rows),
        )

    def register_with_biodock(
        self,
        publication: BiodockExternalTablePublication,
        *,
        rpc_url: str,
        access_token: str | None = None,
    ) -> None:
        """Register the source and table through the BioDock Generator SDK."""
        asyncio.run(
            self._register_with_biodock(
                publication,
                access_token=access_token,
                rpc_url=rpc_url,
            )
        )

    async def _register_with_biodock(
        self,
        publication: BiodockExternalTablePublication,
        *,
        rpc_url: str,
        access_token: str | None = None,
    ) -> None:
        from biodock.berg10.client import (  # type: ignore[import-not-found]
            Berg10RawSourceClientConfig,
            Berg10WebSocketJsonRpcTransport,
        )
        from biodock.generator_sdk.external_sources import (  # type: ignore[import-not-found]
            Berg10ExternalSourceClient,
            structured_table_source_artifact,
        )
        from biodock.generator_sdk.external_tables import (  # type: ignore[import-not-found]
            Berg10ExternalTableClient,
        )

        config = Berg10RawSourceClientConfig(rpc_url=rpc_url, access_token=access_token)
        transport = Berg10WebSocketJsonRpcTransport(config)
        try:
            source = structured_table_source_artifact(
                byte_length=publication.source.byte_length,
                file_count=publication.source.file_count,
                object_fingerprint=publication.source.object_fingerprint,
                raw_locator=publication.source.raw_locator,
                registration_id=publication.source.registration_id,
            )
            source_client = Berg10ExternalSourceClient(cast(BiodockRpcTransport, transport))
            table_client = Berg10ExternalTableClient(cast(BiodockRpcTransport, transport))
            await source_client.register_artifact(source)
            await table_client.declare_source_artifact_table(
                display_name=publication.table.display_name,
                schema_fingerprint=publication.table.schema_fingerprint,
                schema_ref=publication.table.schema_ref,
                source=source,
                table_id=publication.table.table_id,
            )
        finally:
            await transport.aclose()


def _story_rows(run_root: Path, story: JsonMap) -> Iterable[JsonMap]:
    created_at = _string(story.get("created_at"))
    suite_id = _string(story["run_suite_id"])
    run_id = _string(story["run_id"])
    yield _row(
        created_at=created_at,
        event_type="story_ready",
        label="Story review ready",
        run_id=run_id,
        run_suite_id=suite_id,
        sequence=0,
        status=_string(story.get("status"), "complete"),
        payload=story,
    )
    sequence = 1
    for clip in _list_of_maps(story.get("clips")):
        clip_id = _string(clip.get("clip_id"))
        yield _row(
            artifact_path=_string(clip.get("compare_overlay_url")),
            clip_id=clip_id,
            created_at=created_at,
            event_type="clip_summary",
            frame=_int(clip.get("frame_count")),
            label=_string(clip.get("label"), clip_id),
            run_id=run_id,
            run_suite_id=suite_id,
            sequence=sequence,
            status="complete",
            payload=clip,
        )
        sequence += 1
        yield from _clip_event_rows(run_root, suite_id, run_id, clip, created_at, sequence)
        sequence += _clip_event_row_count(run_root, clip)
        yield from _clip_track_rows(run_root, suite_id, run_id, clip, created_at, sequence)
        sequence += _clip_track_row_count(run_root, clip)
    for platform in _list_of_maps(story.get("platforms")):
        yield _row(
            artifact_path=_string(platform.get("path")),
            created_at=created_at,
            event_type="platform_link",
            label=_string(platform.get("label"), _string(platform.get("platform"))),
            run_id=run_id,
            run_suite_id=suite_id,
            sequence=sequence,
            status=_string(platform.get("status"), "unknown"),
            url=_string(platform.get("url")),
            payload=platform,
        )
        sequence += 1


def _clip_event_rows(
    run_root: Path,
    suite_id: str,
    run_id: str,
    clip: JsonMap,
    created_at: str,
    sequence: int,
) -> Iterable[JsonMap]:
    clip_id = _string(clip.get("clip_id"))
    for index, event in enumerate(_artifact_rows(run_root, clip, "events_path", "events")):
        yield _row(
            clip_id=clip_id,
            confidence=_float(event.get("confidence")),
            created_at=created_at,
            decision=_string(event.get("decision")),
            event_type="adapter_decision",
            frame=_int(event.get("frame")),
            label=_string(event.get("display_label"), _string(event.get("reason"))),
            reason=_string(event.get("reason")),
            run_id=run_id,
            run_suite_id=suite_id,
            sequence=sequence + index,
            stage=_string(event.get("stage")),
            status=_string(event.get("decision")),
            track_id=_optional_int(event.get("track_id")),
            payload=event,
        )


def _clip_track_rows(
    run_root: Path,
    suite_id: str,
    run_id: str,
    clip: JsonMap,
    created_at: str,
    sequence: int,
) -> Iterable[JsonMap]:
    clip_id = _string(clip.get("clip_id"))
    for index, track in enumerate(_artifact_rows(run_root, clip, "tracks_path", "tracks")):
        yield _row(
            clip_id=clip_id,
            confidence=_float(track.get("average_confidence")),
            created_at=created_at,
            event_type="mot_track_summary",
            frame=_int(track.get("start_frame")),
            label=f"Track {_string(track.get('track_id'))}",
            run_id=run_id,
            run_suite_id=suite_id,
            sequence=sequence + index,
            status="tracked",
            track_id=_optional_int(track.get("track_id")),
            payload=track,
        )


def _clip_event_row_count(run_root: Path, clip: JsonMap) -> int:
    return len(tuple(_artifact_rows(run_root, clip, "events_path", "events")))


def _clip_track_row_count(run_root: Path, clip: JsonMap) -> int:
    return len(tuple(_artifact_rows(run_root, clip, "tracks_path", "tracks")))


def _artifact_rows(
    run_root: Path,
    clip: JsonMap,
    path_key: str,
    rows_key: str,
) -> Iterable[JsonMap]:
    path = run_root / _string(clip.get(path_key))
    if not path.exists():
        return ()
    payload = _read_json(path)
    return _list_of_maps(payload.get(rows_key))


def _row(
    *,
    run_suite_id: str,
    run_id: str,
    sequence: int,
    event_type: str,
    status: str,
    label: str,
    created_at: str,
    payload: JsonMap,
    artifact_path: str = "",
    clip_id: str = "",
    confidence: float | None = None,
    decision: str = "",
    frame: int | None = None,
    reason: str = "",
    stage: str = "",
    track_id: int | None = None,
    url: str = "",
) -> JsonMap:
    row_id = f"{run_suite_id}:{run_id}:{sequence:08d}:{event_type}"
    sort_key = f"{run_suite_id}:{run_id}:{sequence:08d}"
    return {
        "artifact_path": artifact_path,
        "clip_id": clip_id,
        "confidence": confidence,
        "created_at": created_at,
        "decision": decision,
        "event_type": event_type,
        "frame": frame,
        "label": label,
        "package_id": PACKAGE_ID,
        "payload_json": json.dumps(payload, sort_keys=True),
        "reason": reason,
        "row_id": row_id,
        "run_id": run_id,
        "run_suite_id": run_suite_id,
        "sort_key": sort_key,
        "stage": stage,
        "status": status,
        "track_id": track_id,
        "url": url,
    }


def _read_json(path: Path) -> JsonMap:
    return cast(JsonMap, json.loads(path.read_text(encoding="utf-8")))


def _write_jsonl(path: Path, rows: Iterable[JsonMap]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, separators=(",", ":"), sort_keys=True))
            output.write("\n")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows_filename(suite_id: str, run_id: str) -> str:
    return f"{_safe_path_token(suite_id)}--{_safe_path_token(run_id)}.jsonl"


def _safe_path_token(value: str) -> str:
    safe = [character if character.isalnum() or character in "-_" else "-" for character in value]
    return "".join(safe).strip("-") or "run"


def _list_of_maps(value: Any) -> tuple[JsonMap, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _string(value: object, fallback: str = "") -> str:
    return str(value) if value is not None else fallback


def _int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    return None


def _float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return None


def _optional_int(value: object) -> int | None:
    parsed = _int(value)
    return parsed if parsed is not None and parsed >= 0 else None
