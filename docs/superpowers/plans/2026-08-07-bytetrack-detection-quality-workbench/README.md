# ByteTrack Detection Quality Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-shaped false-positive hand-detection quality workbench that cleans raw detector boxes with ByteTrack MOT, emits auditable corrected detections, supports repeatable experiments, and demonstrates accuracy with labeled and visual review artifacts.

**Architecture:** The adapter is a library-first pipeline with typed boundary parsers, Arrow/NumPy hot-path buffers, a ByteTrack association adapter, pluggable false-positive filters, immutable run storage, MLflow/DVC/Evidently experiment tracking, BioDock Berg10 Generator Package review panels, and static fallback review outputs. The CLI remains a public entrypoint for automation, but the primary user-facing review journey is the BioDock story page. Batch/API/streaming/edge wrappers must reuse the same `AdapterPipeline.run_clip()` core contract.

**Tech Stack:** Python 3.12, `trackers==2.6.0` ByteTrack, `supervision==0.30.0`, `numpy==2.2.6`, `pydantic==2.13.4`, `pyarrow==25.0.0`, `polars==1.43.2`, `plotly==5.24.1`, `opencv-python-headless==4.12.0.88`, `typer==0.27.1`, `structlog==26.1.0`, `opentelemetry-sdk==1.44.0`, `prometheus-client==0.26.0`, `mlflow==3.15.1`, `dvc==3.67.1`, `dvclive==3.49.1`, `evidently==0.7.21`, `ruff==0.16.1`, `mypy==2.3.0`, `fiftyone==0.25.2`, `label-studio-sdk==2.1.0`, `fastapi==0.141.1`, `starlette==0.46.2`, `uvicorn==0.52.1`, `jinja2==3.1.6`, `pyyaml==6.0.3`, `tomlkit==0.15.1`, `python-multipart==0.0.32`.

## Global Constraints

- Scope is false-positive handling only: duplicate merge, implausible size, implausible shape, implausible displacement, unsupported flicker, static scene detections, and max-two wearer-hand selection.
- False-negative interpolation is not implemented and every output run must report `interpolated_detection_count = 0`.
- ByteTrack is mandatory for MOT association. Use `trackers==2.6.0`; use `supervision==0.30.0` only for detection containers and visual annotation helpers.
- The legacy `supervision.ByteTrack` API is not allowed because current Supervision docs deprecate it in favor of the external `trackers` package.
- Every CLI invocation must create a new immutable `RunSuiteId`; every experiment inside that suite must create a new immutable `RunId`; rerunning the same config must never overwrite an earlier run.
- Every experiment must be identified by `ExperimentId`; every input clip must retain `ClipId` provenance from `meta.json`.
- BioDock Berg10 Generator Package integration is mandatory for the visual review journey. Static HTML is a fallback artifact hub only; it must not be the primary customer demo surface.
- MLflow tracking is mandatory for experiment parameters, scalar metrics, tags, and artifacts. The default tracking URI is a Docker-managed MLflow service/profile path; typed config may point to a remote MLflow server later.
- DVC/DVCLive outputs are mandatory for git-friendly metrics and plots under `dvclive/<run_suite_id>/<run_id>/` so regression charts can be compared without reading custom report HTML.
- DVC is the authority for restoring exact data, labels, configs, and experiment workspaces. MLflow, FiftyOne, Label Studio, Rerun, BioDock, Evidently, and static fallback HTML must store links back to the DVC/Git-backed lineage bundle rather than becoming competing lineage stores.
- Evidently reports and workspace links are mandatory for evaluation/regression dashboards where label or metric tables exist; BioDock and static fallback HTML must link to Evidently artifacts instead of reimplementing those charts.
- FiftyOne is mandatory as the visual comparison workbench: each run must create a real FiftyOne dataset with raw detections, cleaned detections, rejected detections, track ids, stage reasons, and hard-case sample tags.
- Label Studio is mandatory as the human correction loop: each run must produce importable pre-annotated tasks, and when a configured Label Studio endpoint is available, the review command must create a per-run project, import predictions through `label-studio-sdk==2.1.0`, and reuse the recorded project on repeated opens of the same immutable run.
- The BioDock story page is the primary visual review hub. The static HTML report is only a fallback hub. Both must link to MLflow, DVC, Evidently, FiftyOne, Label Studio, Rerun, and local artifact paths; neither may duplicate platform features already provided by those tools.
- Every run must write `lineage/replay.lock.json`, containing content-addressed references for git commit, dependency lock hash, dataset DVC hash, label-set DVC hash, canonical config hash, MLflow run id, DVC experiment ref when available, parent lineage id, and baseline run id.
- Human labels must be frozen into immutable `labels/versions/<label_set_id>/` directories before accuracy claims. A label-set id is the SHA-256 of the canonical exported annotations, Label Studio project id, label config hash, task ids, and source frame ids.
- Replay must never mutate the caller's current workspace. `handdetect lineage replay` must create an isolated git worktree under `.handdetect/replays/<replay_id>/worktree`, restore DVC artifacts there, apply typed parameter overrides, run a new experiment that consumes restored worktree inputs but writes child artifacts to the main `runs/`, `mlruns/`, and `dvclive/` roots, compare against the parent run, and publish a new review journey.
- A local workbench must provide one-button replay from a prior run. The workbench may orchestrate DVC/Git/MLflow/Label Studio commands, but it must not duplicate their run comparison, artifact browsing, annotation, or charting features.
- Core logic must not read environment variables, current time, filesystem, network, or random state directly. Public entrypoints create providers and ready handles.
- Pydantic `model_validate` may appear only in boundary parsers for JSON/config/manifest/label imports.
- Internal hot-path transfer is typed object -> NumPy view or Arrow table. Do not serialize to dict/JSON between internal modules.
- Third-party tracker boundaries must use reusable typed scratch buffers when the package requires a native tensor shape; per-frame allocation, `np.concatenate()`, and per-detection Python dict construction are forbidden in the adapter hot path.
- Video frames are decoded only for overlay/report generation. Adapter logic consumes detection/pose/timestamp arrays and must not decode video.
- Files must remain under 450 LOC; functions under 50 LOC; all function parameters and returns must be annotated; `Any` is allowed only at a documented third-party boundary.
- Tests enter through root tasks and public CLIs only. Tests must use the real downloaded dataset, generated run manifests, and production entrypoints; no mocks, monkeypatches, fake clients, fake stores, or hardcoded sample payloads.
- Root task interface must expose `bootstrap`, `doctor`, `run`, `check`, `test`, `verify`, `seed`, `migrate`, and `clean`.
- Custom standalone React is not part of this delivery. The first-class UI must be implemented as BioDock Berg10 Generator Package panels that reuse BioDock frontend packages, FlexLayout, typed generated contracts, Valtio/TanStack Query ownership rules, and `docs/coding-standards-frontend.md`.
- `PACKAGE_BOUNDARIES.md` and `00-reusable-package-boundaries.md` are normative. Reusable logic must live in `packages/*`; `apps/handdetect-cli` may only wire public commands and re-export types for ergonomics.
- Existing task snippets that reference `src/handdetect/...` are logical ownership references. Implementers must place reusable code in the package named by the normative path map and keep `apps/handdetect-cli` thin.
- The code must strictly adhere to `docs/coding-standards.md`, `docs/coding-standards-frontend.md`, and `docs/coding-repo-standards.md`.

---

## 0. BioDock Story Page Normative Amendment

This section supersedes older task wording that treated static HTML, FiftyOne, or Label Studio as the main review UX. Those tools remain integrated, but the main customer-demo surface is the BioDock Berg10 story page described in `docs/superpowers/specs/2026-08-07-workbench-story-page-design.md`.

### Generator Package Mapping

| Concept | Required Value | Implementation Rule |
|---|---|---|
| Generator package name | `handdetect-quality-adapter` | The package is the delivery unit shown by BioDock. |
| `package_id` | `handdetect_quality_adapter` | Use a typed constant; do not repeat raw strings. |
| `workspace_id` | `handdetect_quality_story` | Must be stable across runs so saved BioDock layouts survive refresh. |
| Default layout id | `handdetect_customer_demo_console` | Must extend `berg10.generator.videoReview`. |
| Primary action | `handdetect.run_smoke_experiment` | Must run the smoke flow through a public action/CLI boundary. |
| Package manifest | `generator-package/generator-package-manifest.json` | Validated by BioDock package bundle checks. |
| Workspace descriptor | `generator-package/ui/workspace.json` | Uses BioDock `extends` and `slots`, never hand-written FlexLayout trees in app code. |
| Run event schema | `generator-package/schemas/handdetect-run-event.schema.json` | Raw run events validate once at the boundary. |
| Story views | `generator-package/views/handdetect_story_views.sql` | Projects run artifacts into Berg10-visible rows and artifacts. |
| Theme override | `generator-package/ui/themes/handdetect-story.overrides.css` | Must match or improve the checked-in mock visual contract. |

`external/biodock` is currently a development symlink only. Before implementation is complete, the BioDock dependency must be reproducible through either a pinned submodule commit that contains `berg10.generator.videoReview` or published package dependencies for the required BioDock frontend packages.

### Panel Mapping And Required BioDock Base Layout

BioDock must add `berg10.generator.videoReview` because existing base layouts do not preserve the mock's full-width header, three-column editor center, and full-width bottom timeline.

| Slot | Panels | Purpose |
|---|---|---|
| `slot.status` | `handdetect_story_header` | Run identity, outcome strip, support states, exact platform links. |
| `slot.review` | `handdetect_clip_navigator`, `handdetect_rejection_taxonomy` | Clip/chapter/edge-case navigation and false-positive categories. |
| `slot.primary` | `handdetect_synchronized_viewer` | Frame-locked raw detector vs adapter output review. |
| `slot.inspector` | `handdetect_decision_inspector`, `handdetect_track_explorer` | Selected event explanation and ByteTrack MOT details. |
| `slot.history` | `handdetect_timeline` | Full-width zoomable frame timeline, track lanes, event markers, minimap. |
| `slot.artifacts` | `handdetect_platform_bridge` | Rerun, FiftyOne, MLflow, Label Studio, CVAT, Datumaro, Evidently links. |
| `slot.diagnostics` | `handdetect_diagnostics` | Browser-visible proof, missing artifacts, sync drift, export status, frame budget. |

BioDock implementation must add the layout id to `GENERATOR_BASE_LAYOUT_IDS`, required roles to `GENERATOR_BASE_LAYOUT_REQUIRED_ROLES`, topology to `GENERATOR_BASE_LAYOUT_TOPOLOGY`, a `Video Review` preset, and tests proving `slot.history` stays full width.

### Initial Layout Concepts

| Layout | First-Viewport Story | Required Panels | When To Use |
|---|---|---|---|
| Customer Demo Console | Raw detector on the left, adapter output on the right, timeline below, inspector on the right. | Story Header, Clip Navigator, Synchronized Viewer, Decision Inspector, Rejection Taxonomy, Track Explorer, Timeline, Platform Bridge, Diagnostics. | Default customer/demo mode and smoke-run review. |
| Forensic Review Bay | Four-way input/raw/kept/rejected visual review with engineering filters visible. | Filters/Layers, Rejection Taxonomy, Input Video, Raw Detector, Kept Output, Rejected/Merged, Track Explorer, Source Table Slice. | Engineering debugging and audit defense. |
| Annotation Handoff | Adapter/rejected overlay plus queue of questionable ranges and correction packet. | Rejection Queue, Edge-Case Groups, Adapter Output, Rejected Overlay, Correction Packet, Range Timeline, Platform Bridge. | Human correction in Label Studio now and CVAT in Phase 2. |
| Metrics And Regression | Lineage, stage deltas, regression status, and exact platform links without replacing visual proof. | Run/Lineage, Counts, Stage Deltas, Baseline, Evidently, MLflow, Visual Examples Strip. | Experiment comparison after visual proof is established. |

### Story Page Feature Requirements

The implementation must satisfy all 14 requirements below through the BioDock story page, not only through CLI numbers or static artifacts.

1. Open from the run detail page with one click.
2. First viewport shows the clip review surface, not a report landing page.
3. Support every clip in the run, not sampled stills only.
4. Keep raw input, raw detector overlays, adapter output overlays, rejected/merged overlays, and track overlays frame-synchronized.
5. Provide a zoomable bottom timeline with frame ticks, MOT lanes, rejection markers, duplicate-merge markers, and minimap.
6. Let users jump to previous/next adapter decision event.
7. Let users isolate a ByteTrack track and dim unrelated detections.
8. Show rejection categories as customer-readable classifications.
9. Make every visible box inspectable down to detection id, frame index, timestamp, confidence, track id, stage, reason, and final decision.
10. Show implemented, heuristic candidate, and unsupported states for all hand-detection spec edge cases.
11. Link to the exact MLflow run and matching platform artifacts for the same run.
12. Avoid requiring users to remember CLI commands, URLs, suite ids, or run ids.
13. Degrade visibly when artifacts are missing and show cause plus remediation.
14. Preserve the user journey across BioDock, Rerun, FiftyOne, Label Studio/CVAT, Datumaro, Evidently, MLflow, and DVC through one run-scoped platform manifest.

### Review Artifact Contract

Every run must write compact browser artifacts under `review/`:

- `review/story.json`
- `review/clips/<clip_id>/timeline.json`
- `review/clips/<clip_id>/events.json`
- `review/clips/<clip_id>/tracks.json`
- `review/clips/<clip_id>/chapters.json`
- `review/clips/<clip_id>/raw_overlay.mp4`
- `review/clips/<clip_id>/adapter_overlay.mp4`
- `review/clips/<clip_id>/rejected_overlay.mp4`
- `review/clips/<clip_id>/compare_raw_adapter.mp4`
- `review/clips/<clip_id>/thumbnail_strip.webp`
- `review/platforms.json`

The browser must not load raw Parquet, audit JSONL, large Arrow files, or full source videos for normal UI state. Those remain authoritative artifacts accessed through typed backend routes or platform links.

### Standards Stress-Test Gates

Implementation is not complete unless these gates pass:

- Type safety: all public/internal Python functions are fully annotated; Pydantic v2 owns API/domain contracts; branded ids prevent mixing run, clip, frame, detection, track, label, config, and artifact identities; `mypy --strict` has zero errors.
- Hot-path memory: detection/filter/tracker stages pass validated models, NumPy views, Arrow batches, or Polars lazy frames; no per-detection dicts, no JSON between internal modules, no per-frame `np.concatenate()`, no video decode in adapter logic.
- Zero-copy UI posture: BioDock panels receive URLs, typed ids, scalar states, and compact JSON indexes; video playback uses browser decode; overlays and timeline use canvas/adapters with hot refs; React/Valtio never own frame buffers or per-frame packet queues.
- High-throughput and ultra low-latency: clip workers are bounded; backpressure is explicit; timeline handles 100k events without visible lag; story first contentful UI is under 2 seconds; first playable selected clip is under 5 seconds when overlay videos exist; sync drift is less than 1 frame.
- Observability: phase-level OTel spans, scalar counters/histograms, structured logs with `run_suite_id`, `run_id`, `clip_id`, `phase`, `trace_id`, and relevant artifact ids; no row bytes, Arrow bytes, Parquet bytes, frames, tokens, or presigned URLs in logs/spans; export failures never block core artifacts.
- Resource lifetime: Docker services, MLflow, FiftyOne, Label Studio, Rerun export, CVAT, Datumaro, and Evidently handles are valid-if-created, bounded, and cleaned up by their owning factory/context manager.
- Repo DX: plain `docker compose up -d` starts all first-use infrastructure; every URL and credential needed by a user appears in the root `README.md`; public browser validation uses `10.7.0.4` and port-registry ranges from `docs/coding-repo-standards.md`.
- Frontend standards: no broad Valtio snapshots, no React state for playback frames, no inline styles except third-party viewer adapters, FlexLayout owns topology, dynamic panel registry owns panel selection, stream/session adapters own long-lived push channels.

### Phase 2 Requirements

Phase 2 must add production-shaped integration without changing run lineage semantics:

- CVAT service integration:
  - Add Docker Compose service and typed runtime config using registered ports only.
  - Create run/clip/range-scoped CVAT tasks from the Annotation Handoff layout.
  - Preserve task ids, label schema hash, frame ids, imported prediction ids, reviewer identity where available, and export hash in lineage.
  - Re-import annotations through one boundary parser and freeze labels into immutable `labels/versions/<label_set_id>/`.
- Datumaro export/diff:
  - Export run predictions, frozen labels, CVAT corrections, and baseline comparisons through Datumaro formats.
  - Use Datumaro for dataset conversion/diff rather than custom dataset translators.
  - Write diff manifests and artifact links back into `review/platforms.json`, MLflow, DVC, and the BioDock Platform Bridge.
- Evidently workspace UI:
  - Provide a service-backed Evidently workspace or dashboard link when available, not just detached HTML.
  - Store exact run, baseline, dataset hash, label-set id, config hash, and metric table refs in Evidently metadata.
  - Link exact Evidently workspace/report from BioDock, MLflow artifacts, and static fallback report.

---

## 1. Goal, Non-Goals, Delete List

- Final user-visible outcome:
  - `make run` executes the default experiment suite over `data/`, writes immutable run artifacts under `runs/<run_suite_id>/<run_id>/`, and prints the suite id, each run id, MLflow experiment URL/path, DVC metrics path, and report path.
  - `runs/<run_suite_id>/<run_id>/review/story.json` and clip-scoped review artifacts drive the BioDock story page, including synchronized videos, track lanes, event markers, decision explanations, platform links, and edge-case support states.
  - `runs/<run_suite_id>/<run_id>/report/index.html` remains a fallback hub showing raw-vs-cleaned metrics, filter-stage deltas, regression status, MLflow/DVC/Evidently links, and top error cases.
  - `runs/<run_suite_id>/<run_id>/cleaned/<clip_id>.json` contains corrected detections with at most two final hands per frame.
  - `runs/<run_suite_id>/<run_id>/audit/<clip_id>.jsonl` records every input detection as `kept`, `merged`, or `rejected` with stage, reason, source detection id, destination detection id when merged, track id when available, and provenance.
  - `runs/<run_suite_id>/<run_id>/tables/*.parquet` stores metrics, detections, tracks, and decisions for fast comparison across runs and experiments.
  - `runs/index/run_index.parquet` and `runs/index/metric_history.parquet` append one row per run and per metric so regressions can be queried by `RunSuiteId`, `RunId`, `ExperimentId`, config hash, git commit, dataset hash, label-set id, metric name, and metric value.
  - `handdetect review open --suite-id <id> --run-id <id>` opens or prints stable local URLs for BioDock Story Review, MLflow comparison, FiftyOne visual review, Label Studio correction, Evidently regression report/workspace, DVC plots, Rerun recording, and the static fallback report hub.
  - `handdetect lineage replay --from-run <suite_id>/<run_id> --set adapter.max_center_speed_px_per_s=3900.0` restores the exact parent data/labels/config/code in an isolated worktree, applies the override, runs a child experiment, gates regression against the parent, and opens the new review journey.
  - `handdetect workbench serve` opens the local orchestration surface only when BioDock is unavailable; the preferred run page is BioDock/Berg10 with a replay button, typed parameter overrides, lineage proof, regression status, visual story review, and links into MLflow/DVC/Evidently/FiftyOne/Label Studio/CVAT/Datumaro/Rerun.
- Non-goals:
  - Do not retrain WiLoR, YOLO, or any detector.
  - Do not implement false-negative interpolation.
  - Do not require stereo-depth filtering in the first delivery because no calibration contract is present in the downloaded dataset.
  - Do not build a long-lived web service or streaming runtime in the first delivery.
  - Do not build a standalone custom React frontend in the first delivery. Build BioDock Generator Package panels instead.
- Planned items removed because they do not directly serve the final outcome:
  - Removed DeepStream/GStreamer/Kafka/Flink runtime implementation; record them only in `ARCHITECTURE.md` as deployment targets after the CLI workbench proves the core.
  - Removed custom MOT code; ByteTrack owns association.
  - Removed custom charting app; MLflow, DVC plots, Evidently, BioDock panels, static fallback HTML, Rerun, and FiftyOne export cover interview UX without duplicating platform-owned features.
  - Removed per-frame trace spans; phase-level metrics and sampled visual artifacts give observability without hot-path allocation pressure.

## 2. End-to-End Flow Map

- `data/README.md` and clip folders on disk -> `handdetect.io.dataset.Scanner` -> discovers `ClipPathSet` values with `clip_id`, `meta_path`, `hand_boxes_path`, `frame_ts_path`, `vio_pose_path`, and optional video paths -> `ValidatedClipPathSet` -> validation checks required files and path ownership -> no external call -> clip-level bounded process pool -> no serde, path objects only -> error path emits `HDQ_DATASET_MISSING_FILE`.
- Raw JSON files -> `handdetect.io.parsers.JsonBoundaryParser` -> Pydantic validation into `ValidatedClipBundle` with `ValidatedHandBoxes`, `ValidatedFrameTimestamps`, `ValidatedVioPose`, and `ValidatedClipMeta` -> validation checks frame count, monotonic timestamps, pose length, box coordinates inside declared frame size, and detector uncapped flag -> persistence read only -> no concurrency inside parser -> JSON serde occurs once at boundary -> error path emits `HDQ_INVALID_CLIP_JSON`.
- `ValidatedClipBundle` -> `handdetect.hotpath.columnar.ClipColumnBuilder` -> builds contiguous `DetectionBlock` NumPy arrays and Arrow `RecordBatch` handles -> output owns `DetectionId`, `FrameIndex`, `BoxXYXY`, `Confidence`, `DetectorHandedness`, and `ClipTimestampNs` arrays -> revalidation checks new invariant that array lengths match -> no persistence -> no async -> one allocation per column, no per-detection Python object transfer after this point -> error path emits `HDQ_COLUMNAR_BUILD_FAILED`.
- `DetectionBlock` -> `handdetect.filters.geometric.GeometricFilterPipeline` -> duplicate candidates merged, implausible size/shape rejected, remaining candidate ids passed forward -> output `GeometricStageResult` with decision arrays and candidate mask -> validation checks every source detection has exactly one geometric decision -> no persistence -> vectorized NumPy operations -> no serde -> error path emits `HDQ_GEOMETRIC_FILTER_FAILED`.
- `GeometricStageResult` -> `handdetect.tracking.bytetrack.ByteTrackAssociationAdapter` -> feeds one frame at a time to `trackers.ByteTrackTracker` using NumPy tensor views shaped `[x1, y1, x2, y2, score, class_id]` -> output `TrackBlock` with `TrackId` per surviving candidate plus track lifecycle events -> validation checks frame ids are monotonic and tracker ids are positive for active tracks -> no persistence -> single clip worker, frame loop bounded by clip length -> one tensor view per frame, no JSON serde -> error path emits `HDQ_BYTETRACK_FAILED`.
- `TrackBlock` + VIO pose arrays -> `handdetect.filters.temporal.TemporalFilterPipeline` -> rejects implausible displacement, unsupported short tracks, and static detections under camera motion -> output `TemporalStageResult` with decision arrays and stage metrics -> validation checks every tracked candidate has terminal keep/reject status -> no persistence -> vectorized per-track operations -> no serde -> error path emits `HDQ_TEMPORAL_FILTER_FAILED`.
- `TemporalStageResult` -> `handdetect.selection.max_two.MaxTwoSelector` -> ranks remaining detections by track support, confidence, continuity, and border context -> output `SelectedDetectionBlock` with at most two detections per frame -> validation checks `max_selected_per_frame <= 2` and no interpolated detections -> no persistence -> frame-grouped vectorized ranking -> no serde -> error path emits `HDQ_SELECTOR_FAILED`.
- `SelectedDetectionBlock` + all stage decisions -> `handdetect.audit.ledger.DecisionLedgerWriter` -> writes `audit/<clip_id>.jsonl`, `cleaned/<clip_id>.json`, and Arrow/Parquet tables -> output persisted artifacts plus `ClipRunSummary` -> validation happens on persistence read in regression/eval tasks only -> filesystem writes through `RunArtifactStore` ready handle -> clip-level parallelism with atomic temp-file rename -> serde at external artifact boundary only -> error path emits `HDQ_ARTIFACT_WRITE_FAILED`.
- `RunArtifactStore` persisted tables + optional gold labels -> `handdetect.eval.metrics.EvaluationRunner` -> computes raw-vs-cleaned precision, recall guardrail, false positives per 1k frames, duplicate rate, over-cap frames, and per-stage deltas -> output `EvaluationSummary` and Parquet metrics -> validation of labels at label import boundary -> no network -> bounded clip-level parallelism -> Arrow/Polars lazy scans, no JSON hot path -> error path emits `HDQ_EVAL_FAILED`.
- Run summaries + metrics + decision tables + video references -> `handdetect.review.story_artifacts.StoryArtifactBuilder` -> writes compact BioDock story JSON, timeline/event/track/chapter indexes, thumbnail strips, synchronized overlay videos, and static fallback links -> output run-scoped visual review artifacts -> revalidation of artifact manifests before write -> video decode only in this stage -> bounded frame decoding by clip/sample manifest -> frame copies limited to generated review videos/images -> error path emits `HDQ_STORY_ARTIFACT_FAILED`.
- Story artifacts + package descriptor -> `handdetect.review.biodock_package.HandDetectGeneratorPackagePublisher` -> validates `handdetect-quality-adapter` manifest, writes/updates generator package artifacts, exports Berg10 story views, and records BioDock story URL in `review/platforms.json` -> no adapter hot-path work -> no hand-written FlexLayout tree in app code -> error path emits `HDQ_BIODOCK_PACKAGE_EXPORT_FAILED`.
- Run summaries + metrics + overlay samples -> `handdetect.report.static_report.StaticReportBuilder` and `handdetect.review.fiftyone_export.FiftyOneExporter` -> static fallback HTML, CSS, frame contact sheets, optional overlay videos, and FiftyOne dataset export -> output secondary reviewer artifacts -> revalidation of artifact manifests before report write -> video decode only in this stage -> bounded frame decoding by sample manifest -> frame copies limited to annotation output images/videos -> error path emits `HDQ_REPORT_FAILED`.
- `RunManifest` + `EvaluationSummary` + artifact paths -> `handdetect.tracking_platforms.mlflow_tracker.MlflowExperimentTracker` and `handdetect.tracking_platforms.dvc_tracker.DvcLiveTracker` -> logs parameters, metrics, tags, and artifact references to open-source experiment platforms -> output MLflow run id and DVC metrics/plots path -> tracking backend write through ready handle -> no hot-path async -> scalar metric logging only after clip/run aggregation -> error path emits `HDQ_TRACKING_EXPORT_FAILED` and does not delete run artifacts.
- Current run metrics + baseline manifest + run history index -> `handdetect.regression.gates.RegressionGateRunner` -> compares configured thresholds and records pass/fail -> output `regression.json`, `metric_history.parquet`, Evidently regression report, and CLI exit code -> revalidates persisted current/baseline manifests -> no network unless MLflow tracking URI is remote -> no async -> Polars scans over Parquet, no JSON path -> error path emits `HDQ_REGRESSION_FAILED`.
- `RunManifest` + cleaned/audit/overlay artifacts -> `handdetect.review.fiftyone_dataset.FiftyOneDatasetPublisher` -> creates or updates a real local FiftyOne dataset named `handdetect_<run_suite_id>_<run_id>` with fields `raw`, `cleaned`, `rejected`, `track_id`, `stage_reason`, and `hard_case_tags` -> output dataset name and optional app URL -> FiftyOne API call through review boundary only -> no adapter hot-path work -> error path emits `HDQ_FIFTYONE_EXPORT_FAILED`.
- `RunManifest` + sampled frames + predictions -> `handdetect.review.labelstudio_client.LabelStudioPublisher` -> writes Label Studio JSON tasks with `predictions` and, if endpoint/token are configured, creates a per-run Label Studio project and imports those tasks through the SDK; repeated opens reuse `review/labelstudio-import.json` instead of duplicating tasks -> output project id/url or importable JSON path -> external API call only in review bridge -> no adapter hot-path work -> error path emits `HDQ_LABEL_STUDIO_EXPORT_FAILED`.
- Label Studio project + reviewed annotations -> `handdetect.labels.freeze.LabelSetFreezer` -> exports annotations, canonicalizes task/annotation order, computes `LabelSetId`, writes `labels/versions/<label_set_id>/`, runs `dvc add`, and appends `labels/index.parquet` -> output immutable label version usable by future runs -> SDK/API call only in label boundary -> no adapter hot-path work -> error path emits `HDQ_LABEL_FREEZE_FAILED`.
- Completed run manifest + platform ids + DVC/Git refs -> `handdetect.lineage.capture.LineageSnapshotWriter` -> writes `lineage/replay.lock.json` and logs it to MLflow/DVC artifacts -> output `LineageId` and replay lock -> validates every referenced file hash exists before write -> no concurrency -> JSON only at lineage artifact boundary -> error path emits `HDQ_LINEAGE_CAPTURE_FAILED`.
- Prior `lineage/replay.lock.json` + typed overrides -> `handdetect.lineage.replay.LineageReplayService` -> creates isolated git worktree, restores DVC-tracked data/labels/config, writes child config, runs experiment, compares regression against parent run, exports tracking/review artifacts -> output child run suite, child run id, child lineage id, and comparison URL/path -> subprocess boundaries only for Git/DVC/public CLI -> error path emits `HDQ_LINEAGE_REPLAY_FAILED`.
- Browser click in BioDock story page -> `handdetect.run_smoke_experiment` package action or replay action -> calls public CLI/orchestration service, streams typed job state into Berg10-visible status rows, and updates `review/platforms.json` when complete -> output replay result page and exact platform links -> BioDock owns layout/chrome, HandDetect owns domain panels only -> error path emits `HDQ_BIODOCK_ACTION_FAILED`.
- Browser click in local fallback workbench -> `handdetect.workbench.server` -> calls `LineageReplayService` and streams job status from `runs/<child_suite>/<child_run>/lineage/replay-status.jsonl` -> output replay result page with links to the platform-owned UIs -> FastAPI owns fallback orchestration only -> no custom metrics/annotation/charting UI -> error path emits `HDQ_WORKBENCH_REPLAY_FAILED`.

## 3. Structure Derived From Flow

- Reusable extraction round 1 creates primitive standalone packages:
  - `dq-contracts`: branded ids, enums, status values, and error code contracts.
  - `dq-boundaries`: Raw/Untrusted to Validated parsing, config parsing, canonicalization,
    and hash computation.
  - `dq-resources`: ready handles, provider injection, path builders, command runners,
    clocks, id providers, and resource cleanup ownership.
  - `dq-observability`: metric names, log keys, OTel phase constants, telemetry handles,
    and non-blocking exporter status.
  - `vision-columnar`: NumPy/Arrow detection, track, and decision blocks plus scratch buffers.
  - `vision-geometry`: XYXY boxes, IoU, area/aspect helpers, overlap groups, border proximity,
    and vectorized frame geometry.
  - `mot-interfaces`: tracker protocols, native input/output shapes, and lifecycle events.
  - `decision-ledger`: kept/merged/rejected/interpolated schemas, audit writers, and reason
    registries.
  - `run-artifacts`: immutable run roots, manifests, atomic writes, append-only Parquet
    indexes, file locks, and cleanup by run id.
  - `label-versions`: immutable label-set manifests, annotation canonicalization, label-set
    hashing, and DVC add hooks.
  - `experiment-tracking`: MLflow, DVC/DVCLive, Evidently adapters, and export status.
  - `platform-review`: FiftyOne and Label Studio bridges plus review platform manifests.
  - `vision-review-contracts`: story manifest, clip timeline, event, track, chapter,
    layer, panel, support-state, and platform-link contracts.
- Reusable extraction round 2 creates composites from round 1:
  - `mot-bytetrack`: ByteTrack adapter over `mot-interfaces` and `vision-columnar`.
  - `dq-filter-kit`: reusable filter registries and generic false-positive strategy hooks.
  - `experiment-runner`: suite state machines, bounded execution, run storage, and tracking.
  - `evaluation-regression`: label matching, metrics, calibration, history scans, and gates.
  - `visual-reporting`: sampled overlays, contact sheets, and static report fragments.
  - `vision-review-artifacts`: overlay video generation, compact timeline/event/track
    projections, chapter extraction, thumbnail strips, and Rerun recording manifests.
  - `biodock-generator-package`: HandDetect Generator Package manifest publishing,
    Berg10 view definitions, workspace descriptor validation, and package action wiring.
  - `review-journey`: one-command platform hub over tracking and review bridges.
  - `lineage-replay`: replay locks, DVC/Git refs, isolated worktrees, and typed overrides.
- Reusable extraction round 3 creates the final product-shell package:
  - `replay-workbench`: local FastAPI orchestration UI over lineage replay and platform links.
  - No generic `detector-quality-workbench` package is created in this delivery because only
    the hand-detection app consumes the composition today.
- Fixed point:
  - No additional reusable packages remain after `replay-workbench`.
  - Remaining domain modules are specific to ZED/WiLoR/VIO data or hand behavior.
- Final reusable package list:
  - `dq-contracts`
  - `dq-boundaries`
  - `dq-resources`
  - `dq-observability`
  - `vision-columnar`
  - `vision-geometry`
  - `mot-interfaces`
  - `mot-bytetrack`
  - `dq-filter-kit`
  - `decision-ledger`
  - `run-artifacts`
  - `label-versions`
  - `experiment-tracking`
  - `experiment-runner`
  - `evaluation-regression`
  - `visual-reporting`
  - `platform-review`
  - `review-journey`
  - `vision-review-contracts`
  - `vision-review-artifacts`
  - `biodock-generator-package`
  - `lineage-replay`
  - `replay-workbench`
- Final domain/business module list:
  - `handdetect-domain`: hand-specific policy ids, constants, config, and report vocabulary.
  - `handdetect-io`: this assignment's ZED/WiLoR/VIO JSON/video layout and metadata parser.
  - `handdetect-policies`: hand-specific thresholds, max-two selection, lower-border exit
    assumptions, and false-positive-only first-delivery policy.
  - `apps/handdetect-cli`: Typer commands, config presets, Makefile-visible entrypoints, and
    app-specific wiring only.
- Module ownership rules:
  - Reusable packages must never import `handdetect-domain`, `handdetect-io`,
    `handdetect-policies`, or `handdetect`.
  - Domain packages may import reusable packages and may not duplicate their implementations.
  - `apps/handdetect-cli` may import every package but must not implement algorithms, parsers,
    storage, tracking, review bridges, lineage replay, metrics, or reporting.
  - Existing `src/handdetect/...` references in task snippets are logical references; the
    normative implementation path is the package map in
    `00-reusable-package-boundaries.md`.

## 4. Validation, Resource Lifetime, Boundary Transfer, and Test Plan

- Validation path:
  - `RawClipJson` -> `JsonBoundaryParser.parse_clip()` -> `ValidatedClipBundle` -> internal modules pass validated models and native NumPy/Arrow blocks.
  - `RawExperimentConfig` -> `ExperimentConfigParser.parse_path()` -> `ValidatedExperimentConfig`.
  - `RawGoldLabels` -> `LabelBoundaryParser.parse_coco()` -> `ValidatedGoldLabelSet`.
  - `RawStoryManifest`/`RawPlatformManifest` -> review boundary parsers -> `ValidatedStoryManifest` and `ValidatedPlatformManifest` before BioDock/FiftyOne/Label Studio/Rerun links are published.
- Revalidation triggers:
  - Revalidate after JSON read, YAML/TOML config read, Parquet persistence read, JSONL audit persistence read, CLI user input, and transforms that create `DetectionBlock`, `TrackBlock`, `SelectedDetectionBlock`, or `RunManifest`.
  - Do not fully revalidate between geometric filters, ByteTrack adapter, temporal filters, and selector.
- Boundary transfer:
  - Internal modules receive Pydantic domain models, `numpy.ndarray` views, `pyarrow.RecordBatch`, or `polars.LazyFrame`.
  - Custom DTOs are allowed only for external artifacts: cleaned JSON, audit JSONL, run manifest JSON, regression JSON, label import/export JSON, and compact BioDock review JSON.
- State-machine path:
  - `RunState` values: `created`, `dataset_scanned`, `clips_running`, `artifacts_written`, `evaluated`, `reported`, `regression_checked`, `complete`, `failed`, `cancelled`.
  - `RunEvent` values: `scan_ok`, `clip_started`, `clip_succeeded`, `clip_failed`, `all_clips_succeeded`, `eval_succeeded`, `report_succeeded`, `regression_succeeded`, `failure_seen`, `cancel_requested`.
  - Transition handlers own metrics, log context, artifact manifest updates, and cleanup of temp files.
- RAII path:
  - `RunArtifactStore.open(config, clock, id_provider)` returns a ready handle with non-optional root paths.
  - `RunCatalog.open(runs_root)` returns a ready handle for append-only `run_index.parquet` and `metric_history.parquet`; it must acquire a file lock before appending and release it in the same context manager.
  - `ExperimentTrackingSession.open(config)` returns ready MLflow, DVC, and Evidently handles; remote tracking failures are logged and surfaced in `tracking_export_status.json` but must not mutate completed core artifacts.
  - `ReviewPlatformSession.open(config)` returns ready BioDock, MLflow UI, FiftyOne App, Rerun, and optional Label Studio handles; every launched process has an owning context manager and a status file with pid, URL, and cleanup instructions.
  - `BioDockGeneratorPackageSession.open(config)` returns a ready package publisher with non-optional package root, workspace descriptor path, schema path, theme path, story-view path, and base-layout compatibility proof.
  - `LineageReplaySession.open(snapshot, overrides, paths)` owns the isolated git worktree, DVC pull/apply commands, child process, status log, and cleanup policy.
  - `DatasetScanner.scan(data_root)` returns `ValidatedClipPathSet` values only after required data path checks pass.
  - `TelemetryHandle.open(config)` returns a ready handle whose exporter failures are non-blocking.
  - Factories use `contextlib.ExitStack` so temp directories and file handles are cleaned by the owner that acquired them.
- Test path:
  - `make seed` builds `runs/seed/seed-manifest.json` from real `data/` clip ids and records a small deterministic smoke subset.
  - `make test` runs public CLI acceptance tests against that seed manifest and real dataset files.
  - Acceptance tests assert user-visible artifacts: run manifest, cleaned JSON, audit JSONL, Parquet metrics, BioDock story manifest, overlay videos, platform manifest, static fallback HTML report, and regression pass/fail JSON.
  - Acceptance tests run the same smoke config twice and assert two distinct run ids, two distinct artifact roots, two MLflow runs, and at least two rows in `runs/index/run_index.parquet`.
  - Browser acceptance tests load BioDock through `http://10.7.0.4:60050`, run smoke from a button, open Story Review, play/scrub the selected clip, select a rejection marker, isolate a track, and verify exact platform links.
  - Drift guards scan source for forbidden patterns such as mocks, internal validation leakage, unpinned dependencies, and deprecated `supervision.ByteTrack`.

## 5. Reuse and Performance Plan

- ByteTrack MOT:
  - Selected package: `trackers==2.6.0`, Apache-2.0, `ByteTrackTracker`.
  - Rejected package: legacy `supervision.ByteTrack`; rejected because Supervision current docs deprecate it and direct users to `trackers`.
  - Hot stage: `ByteTrackAssociationAdapter.associate_clip()`.
  - Copy/serde removed: build frame tensors through `ByteTrackTensorScratch`, a reusable `float32` buffer sized to the maximum candidate count for the clip; do not create per-detection Python dicts, per-frame concatenations, or JSON payloads for tracker input.
  - Zero-copy boundary rule: `DetectionBlock` columns move by reference across internal filters; the only ByteTrack data movement is filling the reusable native tensor required by `trackers.ByteTrackTracker`.
  - Batching/concurrency: one tracker instance per clip; clip-level process pool bounded by `RuntimeConfig.max_clip_workers`.
  - Backpressure: CLI waits on bounded process futures; no unbounded task submission.
- Columnar analytics:
  - Selected packages: `pyarrow==25.0.0`, `polars==1.43.2`.
  - Rejected custom CSV metrics; rejected because CSV would force string parsing and weak schema tracking across experiments.
  - Hot stage: metrics and regression over detections/tracks/decisions.
  - Copy/serde removed: persisted Parquet is scanned lazily by Polars; JSONL is for audit humans and not used for metrics hot path.
- Open-source experiment tracking:
  - Selected packages: `mlflow==3.15.1`, `dvc==3.67.1`, `dvclive==3.49.1`, `evidently==0.7.21`.
  - Rejected custom SQL dashboard; rejected because MLflow/DVC/Evidently already provide mature run tracking, metric comparison, plots, and reports.
  - Hot stage: none. Tracking export runs after aggregation, logs scalar metrics and artifact references, and must not run inside per-frame loops.
  - Copy/serde removed: MLflow and DVCLive receive scalar metrics from `EvaluationSummary`; Evidently reads Arrow/Parquet-derived Pandas/Polars frames only in reporting, not adapter processing.
- Lineage restore:
  - Selected authority: DVC experiments and DVC-tracked data/label/config artifacts.
  - Rejected MLflow-only restore; rejected because MLflow is excellent for comparison but does not own exact workspace/data checkout.
  - Rejected manual Git checkout instructions; rejected because replay must be a one-command or one-button operator action.
  - Hot stage: none. Restore/replay happens before a child experiment starts and uses an isolated worktree.
- Local replay workbench:
  - Selected packages: `fastapi==0.141.1`, `uvicorn==0.52.1`, `jinja2==3.1.6`.
  - Rejected standalone custom React workbench; rejected because BioDock Generator Package panels own the first-class review UI and local FastAPI is only fallback/orchestration.
  - Hot stage: none. The fallback workbench streams status files and invokes public CLI services; it never processes frames.
- BioDock Generator Package UI:
  - Selected packages: BioDock `generator-workspace-runtime`, `generator-workspace-host-adapters`, `scientific-workspace`, `flexlayout-topology-adapter`, `browser-diagnostics`, `viewer-hot-state-refs`, `lifecycle-leases`, and `scientific-presentation-controls`.
  - Rejected hand-authored FlexLayout JSON in HandDetect app code; rejected because BioDock `extends` plus slot overrides already owns layout compilation and persistence.
  - Rejected React-owned playback state; rejected because video/canvas hot state must live in viewer adapters/hot refs and publish only coarse typed state to React/Valtio.
  - Hot stage: video playback and timeline interaction only. Panels receive compact JSON indexes and URLs, not raw tables or frame buffers.
- Open-source review platforms:
  - Selected packages/platforms: BioDock for the integrated story page, Rerun for temporal/MOT playback, FiftyOne App for visual side-by-side inspection and filtering, Label Studio plus `label-studio-sdk==2.1.0` for correction/label approval, MLflow UI for experiment comparison, DVC plots for git-friendly metric history, Evidently reports/workspace for regression/evaluation reports, CVAT and Datumaro in Phase 2.
  - Rejected duplicating platform internals; rejected because these tools already own run comparison, visual CV review, annotation correction, dataset diff/export, and metrics plots.
  - Hot stage: none. Review platform export happens after run artifacts are complete and reads persisted Arrow/Parquet/JSONL artifacts through typed boundary readers.
- Schemas and type safety:
  - Selected package: `pydantic==2.13.4`.
  - Rejected raw dict parsing; rejected because domain identity and validation state must be impossible to erase.
  - Hot stage: no Pydantic models inside per-frame filter loops.
- Visual artifacts:
  - Selected packages: `opencv-python-headless==4.12.0.88`, `supervision==0.30.0`, `fiftyone==0.25.2`.
  - Rejected custom annotation editor; rejected because Label Studio/CVAT own correction and BioDock owns presentation.
  - Hot stage: visual report is not adapter hot path. It decodes sampled frames only, from `SampleManifest`.
- Observability:
  - Selected packages: `structlog==26.1.0`, `opentelemetry-sdk==1.44.0`, `prometheus-client==0.26.0`.
  - Hot stage: phase-level counters and histograms only. Per-detection decisions go to audit artifacts, not logs/spans.

## 6. Second-Pass Audit

- Deleted low-value features:
  - Removed production streaming runtime from first implementation and kept only the reusable core contract plus architecture doc.
  - Removed standalone custom React workbench; retained BioDock Generator Package panels plus static fallback HTML/FiftyOne/Label Studio/Rerun export paths.
- Removed duplicate concepts:
  - Collapsed separate run history, experiment history, and provenance stores into `RunArtifactStore` plus `RunManifest`.
  - Re-expanded cross-run history into `RunCatalog` after audit because `RunArtifactStore` alone cannot support easy regression queries without scanning every run directory.
  - Collapsed separate tracker and temporal association concepts into `ByteTrackAssociationAdapter` followed by temporal false-positive filters.
- Reused package/helper:
  - ByteTrack association uses `trackers.ByteTrackTracker`.
  - Annotation and detection containers use Supervision.
  - Metrics tables use Arrow/Polars.
  - Experiment tracking uses MLflow, DVC/DVCLive, and Evidently instead of a custom dashboard/database.
  - Story review uses BioDock Generator Package panels and Rerun/FiftyOne/Label Studio links instead of a closed custom CV platform.
  - Exact replay uses DVC/Git worktrees instead of a custom lineage database.
  - Reusable implementation boundaries are now standalone `packages/*` packages instead of
    duplicated `handdetect.*` modules.
- Reduced copy/serde:
  - JSON parse occurs once at input boundary.
  - Filter/tracker stages exchange NumPy/Arrow blocks.
  - Metrics compare Parquet tables instead of reading audit JSONL.
- Validation state:
  - Untrusted input names are confined to `handdetect.io` and `handdetect.config`.
  - Internal modules accept `Validated*` models or native columnar blocks only.
- Boundary transfer:
  - Public CLI passes typed config and ready handles into pipeline.
  - External artifact formats are written only by audit/report/run store modules.
  - Experiment tracker adapters receive typed run summaries and artifact paths; domain modules never import MLflow, DVC, or Evidently.
- RAII/resource ownership:
  - Dataset, run store, telemetry, video reader, and label store each have factory/context-manager ownership.
- Test realism:
  - Acceptance tests run public CLIs over real `data/` clips and assert real artifacts.
  - No fake detector outputs are introduced.
- Frontend re-render avoidance:
  - No standalone React frontend is added. BioDock panels must use existing frontend packages; playback frames, timeline hover, and canvas draw state stay in hot refs/adapters rather than React render state.

## Plan Files

- [00-reusable-package-boundaries.md](./00-reusable-package-boundaries.md): fixed-point reusable pattern extraction, final package list, domain module list, and package-boundary drift guard.
- [01-repo-dx-contracts.md](./01-repo-dx-contracts.md): repository scaffold, pinned dependencies, root task interface, typed domain contracts, config, observability constants.
- [02-io-columnar-run-store.md](./02-io-columnar-run-store.md): dataset scanning, validation boundaries, columnar memory layout, run artifact store.
- [03-bytetrack-adapter-and-filters.md](./03-bytetrack-adapter-and-filters.md): ByteTrack adapter, geometric filters, temporal filters, max-two selector, audit decisions.
- [04-pipeline-experiments-provenance.md](./04-pipeline-experiments-provenance.md): state-machine orchestration, experiment matrices, immutable run provenance, bounded concurrency.
- [05-evaluation-regression.md](./05-evaluation-regression.md): gold-label import, accuracy metrics, calibration sweeps, regression gates.
- [06-reporting-review-workbench.md](./06-reporting-review-workbench.md): BioDock story artifacts, synchronized overlays, Rerun/FiftyOne/Label Studio exports, static fallback report, architecture docs.
- [07-open-source-experiment-tracking.md](./07-open-source-experiment-tracking.md): MLflow, DVC/DVCLive, Evidently, append-only run catalog, cross-run regression query path.
- [08-seamless-review-journey.md](./08-seamless-review-journey.md): one-command review journey across BioDock, Rerun, MLflow, DVC, Evidently, FiftyOne, Label Studio, and the static fallback hub.
- [09-lineage-restore-replay-workbench.md](./09-lineage-restore-replay-workbench.md): DVC/Git-backed lineage bundles, immutable label versions, isolated restore/replay, and one-button local replay UX.
