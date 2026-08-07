# ByteTrack Detection Quality Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-shaped false-positive hand-detection quality workbench that cleans raw detector boxes with ByteTrack MOT, emits auditable corrected detections, supports repeatable experiments, and demonstrates accuracy with labeled and visual review artifacts.

**Architecture:** The adapter is a library-first pipeline with typed boundary parsers, Arrow/NumPy hot-path buffers, a ByteTrack association adapter, pluggable false-positive filters, immutable run storage, MLflow/DVC/Evidently experiment tracking, and static review outputs. The CLI is the first public entrypoint; batch/API/streaming/edge wrappers must reuse the same `AdapterPipeline.run_clip()` core contract.

**Tech Stack:** Python 3.12, `trackers==2.6.0` ByteTrack, `supervision==0.30.0`, `numpy==2.5.1`, `pydantic==2.13.4`, `pyarrow==25.0.0`, `polars==1.43.2`, `opencv-python-headless==5.0.0.93`, `typer==0.27.1`, `structlog==26.1.0`, `opentelemetry-sdk==1.44.0`, `prometheus-client==0.26.0`, `mlflow==3.15.1`, `dvc==3.67.1`, `dvclive==3.49.1`, `evidently==0.7.21`, `ruff==0.16.1`, `mypy==2.3.0`, `fiftyone==1.20.1`, `label-studio-sdk==2.1.0`.

## Global Constraints

- Scope is false-positive handling only: duplicate merge, implausible size, implausible shape, implausible displacement, unsupported flicker, static scene detections, and max-two wearer-hand selection.
- False-negative interpolation is not implemented and every output run must report `interpolated_detection_count = 0`.
- ByteTrack is mandatory for MOT association. Use `trackers==2.6.0`; use `supervision==0.30.0` only for detection containers and visual annotation helpers.
- The legacy `supervision.ByteTrack` API is not allowed because current Supervision docs deprecate it in favor of the external `trackers` package.
- Every CLI invocation must create a new immutable `RunSuiteId`; every experiment inside that suite must create a new immutable `RunId`; rerunning the same config must never overwrite an earlier run.
- Every experiment must be identified by `ExperimentId`; every input clip must retain `ClipId` provenance from `meta.json`.
- MLflow tracking is mandatory for experiment parameters, scalar metrics, tags, and artifacts. The default tracking URI is local `mlruns/`; a typed config value may point to a remote MLflow server later.
- DVC/DVCLive outputs are mandatory for git-friendly metrics and plots under `dvclive/<run_suite_id>/<run_id>/` so regression charts can be compared without reading custom report HTML.
- Evidently reports are mandatory for evaluation/regression dashboards where label or metric tables exist; static HTML must link to Evidently artifacts instead of reimplementing those charts.
- FiftyOne is mandatory as the visual comparison workbench: each run must create a real FiftyOne dataset with raw detections, cleaned detections, rejected detections, track ids, stage reasons, and hard-case sample tags.
- Label Studio is mandatory as the human correction loop: each run must produce importable pre-annotated tasks, and when a configured Label Studio endpoint is available, the review command must create a per-run project, import predictions through `label-studio-sdk==2.1.0`, and reuse the recorded project on repeated opens of the same immutable run.
- The static HTML report is only a hub. It must link to MLflow, DVC, Evidently, FiftyOne, Label Studio, and local artifact paths; it must not duplicate platform features already provided by those tools.
- Core logic must not read environment variables, current time, filesystem, network, or random state directly. Public entrypoints create providers and ready handles.
- Pydantic `model_validate` may appear only in boundary parsers for JSON/config/manifest/label imports.
- Internal hot-path transfer is typed object -> NumPy view or Arrow table. Do not serialize to dict/JSON between internal modules.
- Third-party tracker boundaries must use reusable typed scratch buffers when the package requires a native tensor shape; per-frame allocation, `np.concatenate()`, and per-detection Python dict construction are forbidden in the adapter hot path.
- Video frames are decoded only for overlay/report generation. Adapter logic consumes detection/pose/timestamp arrays and must not decode video.
- Files must remain under 450 LOC; functions under 50 LOC; all function parameters and returns must be annotated; `Any` is allowed only at a documented third-party boundary.
- Tests enter through root tasks and public CLIs only. Tests must use the real downloaded dataset, generated run manifests, and production entrypoints; no mocks, monkeypatches, fake clients, fake stores, or hardcoded sample payloads.
- Root task interface must expose `bootstrap`, `doctor`, `run`, `check`, `test`, `verify`, `seed`, `migrate`, and `clean`.
- Custom React is not part of this first delivery. Static HTML/FiftyOne/Label Studio exports provide UX; if a React UI is added later it must follow `docs/coding-standards-frontend.md`.
- The code must strictly adhere to `docs/coding-standards.md`, `docs/coding-standards-frontend.md`, and `docs/coding-repo-standards.md`.

---

## 1. Goal, Non-Goals, Delete List

- Final user-visible outcome:
  - `make run` executes the default experiment suite over `data/`, writes immutable run artifacts under `runs/<run_suite_id>/<run_id>/`, and prints the suite id, each run id, MLflow experiment URL/path, DVC metrics path, and report path.
  - `runs/<run_suite_id>/<run_id>/report/index.html` shows raw-vs-cleaned metrics, filter-stage deltas, visual before/after examples, regression status, MLflow/DVC/Evidently links, and top error cases.
  - `runs/<run_suite_id>/<run_id>/cleaned/<clip_id>.json` contains corrected detections with at most two final hands per frame.
  - `runs/<run_suite_id>/<run_id>/audit/<clip_id>.jsonl` records every input detection as `kept`, `merged`, or `rejected` with stage, reason, source detection id, destination detection id when merged, track id when available, and provenance.
  - `runs/<run_suite_id>/<run_id>/tables/*.parquet` stores metrics, detections, tracks, and decisions for fast comparison across runs and experiments.
  - `runs/index/run_index.parquet` and `runs/index/metric_history.parquet` append one row per run and per metric so regressions can be queried by `RunSuiteId`, `RunId`, `ExperimentId`, config hash, git commit, dataset hash, label-set id, metric name, and metric value.
  - `handdetect review open --suite-id <id> --run-id <id>` opens or prints stable local URLs for MLflow comparison, FiftyOne visual review, Label Studio correction, Evidently regression report, DVC plots, and the static report hub.
- Non-goals:
  - Do not retrain WiLoR, YOLO, or any detector.
  - Do not implement false-negative interpolation.
  - Do not require stereo-depth filtering in the first delivery because no calibration contract is present in the downloaded dataset.
  - Do not build a long-lived web service or streaming runtime in the first delivery.
  - Do not build a custom React frontend in the first delivery.
- Planned items removed because they do not directly serve the final outcome:
  - Removed DeepStream/GStreamer/Kafka/Flink runtime implementation; record them only in `ARCHITECTURE.md` as deployment targets after the CLI workbench proves the core.
  - Removed custom MOT code; ByteTrack owns association.
  - Removed custom charting app; MLflow, DVC plots, Evidently, static HTML, and FiftyOne export cover interview UX without adding frontend state complexity.
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
- Run summaries + metrics + overlay samples -> `handdetect.report.static_report.StaticReportBuilder` and `handdetect.review.fiftyone_export.FiftyOneExporter` -> static HTML, CSS, frame contact sheets, optional overlay videos, and FiftyOne dataset export -> output reviewer UX artifacts -> revalidation of artifact manifests before report write -> video decode only in this stage -> bounded frame decoding by sample manifest -> frame copies limited to annotation output images/videos -> error path emits `HDQ_REPORT_FAILED`.
- `RunManifest` + `EvaluationSummary` + artifact paths -> `handdetect.tracking_platforms.mlflow_tracker.MlflowExperimentTracker` and `handdetect.tracking_platforms.dvc_tracker.DvcLiveTracker` -> logs parameters, metrics, tags, and artifact references to open-source experiment platforms -> output MLflow run id and DVC metrics/plots path -> tracking backend write through ready handle -> no hot-path async -> scalar metric logging only after clip/run aggregation -> error path emits `HDQ_TRACKING_EXPORT_FAILED` and does not delete run artifacts.
- Current run metrics + baseline manifest + run history index -> `handdetect.regression.gates.RegressionGateRunner` -> compares configured thresholds and records pass/fail -> output `regression.json`, `metric_history.parquet`, Evidently regression report, and CLI exit code -> revalidates persisted current/baseline manifests -> no network unless MLflow tracking URI is remote -> no async -> Polars scans over Parquet, no JSON path -> error path emits `HDQ_REGRESSION_FAILED`.
- `RunManifest` + cleaned/audit/overlay artifacts -> `handdetect.review.fiftyone_dataset.FiftyOneDatasetPublisher` -> creates or updates a real local FiftyOne dataset named `handdetect_<run_suite_id>_<run_id>` with fields `raw`, `cleaned`, `rejected`, `track_id`, `stage_reason`, and `hard_case_tags` -> output dataset name and optional app URL -> FiftyOne API call through review boundary only -> no adapter hot-path work -> error path emits `HDQ_FIFTYONE_EXPORT_FAILED`.
- `RunManifest` + sampled frames + predictions -> `handdetect.review.labelstudio_client.LabelStudioPublisher` -> writes Label Studio JSON tasks with `predictions` and, if endpoint/token are configured, creates a per-run Label Studio project and imports those tasks through the SDK; repeated opens reuse `review/labelstudio-import.json` instead of duplicating tasks -> output project id/url or importable JSON path -> external API call only in review bridge -> no adapter hot-path work -> error path emits `HDQ_LABEL_STUDIO_EXPORT_FAILED`.

## 3. Structure Derived From Flow

- First reusable pattern round:
  - Typed boundary parser: `handdetect.io.parsers` validates external JSON/config/labels once and returns domain models.
  - Run artifact store: `handdetect.runs.store` owns immutable output paths, atomic writes, manifests, and cleanup by `RunId`.
  - Run catalog: `handdetect.runs.catalog` owns append-only run and metric history tables for cross-run queries.
  - Columnar block: `handdetect.hotpath.columnar` owns NumPy/Arrow memory layout for detections, tracks, and decisions.
  - Filter registry: `handdetect.filters.registry` maps typed `FilterName` to `FilterStrategy` without if/else chains.
  - Tracker adapter: `handdetect.tracking.interfaces` isolates third-party MOT libraries behind typed native input/output shapes.
  - Metrics registry: `handdetect.metrics.registry` centralizes metric names, counters, histograms, and report query ids.
  - Experiment tracker adapters: `handdetect.tracking_platforms` isolates MLflow, DVC/DVCLive, and Evidently from domain logic.
  - State-machine runner: `handdetect.pipeline.state_machine` owns job and clip phase transitions.
- Second reusable pattern round:
  - Experiment engine: `handdetect.experiments.runner` composes config, run store, pipeline, metrics, and regression gates into repeatable experiment suites.
  - Review artifact builder: `handdetect.report` composes persisted tables and sample manifests into HTML/visual outputs.
  - Label/evaluation workbench: `handdetect.eval` composes label imports, IoU matching, stage metrics, and calibration sweeps.
  - Review journey bridge: `handdetect.review_journey` composes MLflow, DVC, Evidently, FiftyOne, Label Studio, and static report links into one operator-facing command.
- Final module list:
  - `handdetect.config`: typed runtime and experiment configuration.
  - `handdetect.domain`: Pydantic domain models, branded ids, enums, constants.
  - `handdetect.io`: dataset scanning and boundary parsing.
  - `handdetect.hotpath`: NumPy/Arrow columnar blocks and vectorized geometry helpers.
  - `handdetect.filters`: geometric and temporal false-positive filters.
  - `handdetect.tracking`: ByteTrack adapter and tracker interfaces.
  - `handdetect.selection`: max-two final hand selection.
  - `handdetect.audit`: decision ledger and cleaned detection writer.
  - `handdetect.pipeline`: state-machine orchestration and bounded clip execution.
  - `handdetect.runs`: immutable run store, provenance, manifests, and cleanup.
  - `handdetect.tracking_platforms`: open-source experiment tracking adapters for MLflow, DVC/DVCLive, and Evidently.
  - `handdetect.experiments`: experiment matrix execution and comparison.
  - `handdetect.eval`: labels, IoU matching, accuracy metrics, calibration sweeps.
  - `handdetect.report`: static HTML, sampled overlays, FiftyOne export.
  - `handdetect.review_journey`: public review launcher and platform URL/status manifest.
  - `handdetect.regression`: baseline comparison and pass/fail gates.
  - `handdetect.cli`: public Typer commands only.
- Module ownership rules:
  - `handdetect.domain` owns type names and enums; it never reads files or runs algorithms.
  - `handdetect.io` owns untrusted data validation; it never filters detections or writes run artifacts.
  - `handdetect.hotpath` owns memory layout; it never knows filesystem paths or experiment ids.
  - `handdetect.tracking` owns ByteTrack integration; it never decides false-positive policy beyond tracker association.
  - `handdetect.filters` owns decision policies; it never writes JSON/Parquet.
  - `handdetect.pipeline` owns state transitions; it never parses raw JSON or formats reports.
  - `handdetect.report` owns reviewer artifacts; it never changes cleaned detections.

## 4. Validation, Resource Lifetime, Boundary Transfer, and Test Plan

- Validation path:
  - `RawClipJson` -> `JsonBoundaryParser.parse_clip()` -> `ValidatedClipBundle` -> internal modules pass validated models and native NumPy/Arrow blocks.
  - `RawExperimentConfig` -> `ExperimentConfigParser.parse_path()` -> `ValidatedExperimentConfig`.
  - `RawGoldLabels` -> `LabelBoundaryParser.parse_coco()` -> `ValidatedGoldLabelSet`.
- Revalidation triggers:
  - Revalidate after JSON read, YAML/TOML config read, Parquet persistence read, JSONL audit persistence read, CLI user input, and transforms that create `DetectionBlock`, `TrackBlock`, `SelectedDetectionBlock`, or `RunManifest`.
  - Do not fully revalidate between geometric filters, ByteTrack adapter, temporal filters, and selector.
- Boundary transfer:
  - Internal modules receive Pydantic domain models, `numpy.ndarray` views, `pyarrow.RecordBatch`, or `polars.LazyFrame`.
  - Custom DTOs are allowed only for external artifacts: cleaned JSON, audit JSONL, run manifest JSON, regression JSON, and label import/export JSON.
- State-machine path:
  - `RunState` values: `created`, `dataset_scanned`, `clips_running`, `artifacts_written`, `evaluated`, `reported`, `regression_checked`, `complete`, `failed`, `cancelled`.
  - `RunEvent` values: `scan_ok`, `clip_started`, `clip_succeeded`, `clip_failed`, `all_clips_succeeded`, `eval_succeeded`, `report_succeeded`, `regression_succeeded`, `failure_seen`, `cancel_requested`.
  - Transition handlers own metrics, log context, artifact manifest updates, and cleanup of temp files.
- RAII path:
  - `RunArtifactStore.open(config, clock, id_provider)` returns a ready handle with non-optional root paths.
  - `RunCatalog.open(runs_root)` returns a ready handle for append-only `run_index.parquet` and `metric_history.parquet`; it must acquire a file lock before appending and release it in the same context manager.
  - `ExperimentTrackingSession.open(config)` returns ready MLflow, DVC, and Evidently handles; remote tracking failures are logged and surfaced in `tracking_export_status.json` but must not mutate completed core artifacts.
  - `ReviewPlatformSession.open(config)` returns ready MLflow UI, FiftyOne App, and optional Label Studio handles; every launched process has an owning context manager and a status file with pid, URL, and cleanup instructions.
  - `DatasetScanner.scan(data_root)` returns `ValidatedClipPathSet` values only after required data path checks pass.
  - `TelemetryHandle.open(config)` returns a ready handle whose exporter failures are non-blocking.
  - Factories use `contextlib.ExitStack` so temp directories and file handles are cleaned by the owner that acquired them.
- Test path:
  - `make seed` builds `runs/seed/seed-manifest.json` from real `data/` clip ids and records a small deterministic smoke subset.
  - `make test` runs public CLI acceptance tests against that seed manifest and real dataset files.
  - Acceptance tests assert user-visible artifacts: run manifest, cleaned JSON, audit JSONL, Parquet metrics, HTML report, and regression pass/fail JSON.
  - Acceptance tests run the same smoke config twice and assert two distinct run ids, two distinct artifact roots, two MLflow runs, and at least two rows in `runs/index/run_index.parquet`.
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
- Open-source review platforms:
  - Selected packages/platforms: FiftyOne App for visual side-by-side sample inspection, Label Studio plus `label-studio-sdk==2.1.0` for correction/label approval, MLflow UI for experiment comparison, DVC plots for git-friendly metric history, Evidently HTML for regression/evaluation reports.
  - Rejected custom comparison UI; rejected because these tools already own run comparison, visual CV review, pre-annotation correction, and metrics plots.
  - Hot stage: none. Review platform export happens after run artifacts are complete and reads persisted Arrow/Parquet/JSONL artifacts through typed boundary readers.
- Schemas and type safety:
  - Selected package: `pydantic==2.13.4`.
  - Rejected raw dict parsing; rejected because domain identity and validation state must be impossible to erase.
  - Hot stage: no Pydantic models inside per-frame filter loops.
- Visual artifacts:
  - Selected packages: `opencv-python-headless==5.0.0.93`, `supervision==0.30.0`, `fiftyone==1.20.1`.
  - Rejected custom annotation viewer in first delivery; rejected because static report plus FiftyOne gives stronger UX with less custom frontend risk.
  - Hot stage: visual report is not adapter hot path. It decodes sampled frames only, from `SampleManifest`.
- Observability:
  - Selected packages: `structlog==26.1.0`, `opentelemetry-sdk==1.44.0`, `prometheus-client==0.26.0`.
  - Hot stage: phase-level counters and histograms only. Per-detection decisions go to audit artifacts, not logs/spans.

## 6. Second-Pass Audit

- Deleted low-value features:
  - Removed production streaming runtime from first implementation and kept only the reusable core contract plus architecture doc.
  - Removed custom React workbench and retained static HTML/FiftyOne/Label Studio export paths.
- Removed duplicate concepts:
  - Collapsed separate run history, experiment history, and provenance stores into `RunArtifactStore` plus `RunManifest`.
  - Re-expanded cross-run history into `RunCatalog` after audit because `RunArtifactStore` alone cannot support easy regression queries without scanning every run directory.
  - Collapsed separate tracker and temporal association concepts into `ByteTrackAssociationAdapter` followed by temporal false-positive filters.
- Reused package/helper:
  - ByteTrack association uses `trackers.ByteTrackTracker`.
  - Annotation and detection containers use Supervision.
  - Metrics tables use Arrow/Polars.
  - Experiment tracking uses MLflow, DVC/DVCLive, and Evidently instead of a custom dashboard/database.
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
  - No React frontend is added, so frontend render-state rules are avoided in first delivery.

## Plan Files

- [01-repo-dx-contracts.md](./01-repo-dx-contracts.md): repository scaffold, pinned dependencies, root task interface, typed domain contracts, config, observability constants.
- [02-io-columnar-run-store.md](./02-io-columnar-run-store.md): dataset scanning, validation boundaries, columnar memory layout, run artifact store.
- [03-bytetrack-adapter-and-filters.md](./03-bytetrack-adapter-and-filters.md): ByteTrack adapter, geometric filters, temporal filters, max-two selector, audit decisions.
- [04-pipeline-experiments-provenance.md](./04-pipeline-experiments-provenance.md): state-machine orchestration, experiment matrices, immutable run provenance, bounded concurrency.
- [05-evaluation-regression.md](./05-evaluation-regression.md): gold-label import, accuracy metrics, calibration sweeps, regression gates.
- [06-reporting-review-workbench.md](./06-reporting-review-workbench.md): HTML report, visual overlays/contact sheets, FiftyOne/Label Studio exports, architecture docs.
- [07-open-source-experiment-tracking.md](./07-open-source-experiment-tracking.md): MLflow, DVC/DVCLive, Evidently, append-only run catalog, cross-run regression query path.
- [08-seamless-review-journey.md](./08-seamless-review-journey.md): one-command review journey across MLflow, DVC, Evidently, FiftyOne, Label Studio, and the static report hub.
