# Package Boundaries

## Reuse-First Rule

Before creating a new package, check existing BioDock packages and selected mature
open-source platforms first. If a capability is already close enough, extend that owner
instead of creating a parallel HandDetect implementation.

## Product Ownership Boundary

HandDetect is a standalone detector-quality adapter. It must run through CLI or automation
without Berg10, BioDock services, or a browser. BioDock is an optional UI/runtime host used
through the Generator SDK and package descriptors.

- HandDetect owns core processing, ByteTrack invocation, false-positive decisions, run
  artifacts, platform exports, local fallback review artifacts, and CLI/workbench fallback
  orchestration.
- BioDock owns Berg10, the Generator SDK, reusable package-authoring helpers, reusable base
  layouts, generic panels, FlexLayout compilation, C-view projection, diagnostics, frontend
  chrome, and viewer lifecycle.
- Berg10 must not depend on HandDetect. HandDetect is one generator package among many.
- Reusable SDK or UI-host code belongs in `external/biodock`; this repo may keep only
  HandDetect-specific generator package metadata, SQL views, theme overrides, action identity,
  and fallback story artifacts.

## Existing Owners To Reuse

- BioDock `generator-workspace-runtime`: generator descriptors, actions, selectors, evidence.
- BioDock `generator-workspace-host-adapters` and `flexlayout-topology-adapter`: layout compilation.
- BioDock `scientific-workspace` and `generator-workspace-react`: panel hosting and workspace chrome.
- BioDock `artifact-viewer-adapter-registry`: artifact viewer adapter manifests.
- BioDock `browser-diagnostics`, `viewer-hot-state-refs`, `lifecycle-leases`: diagnostics, hot viewer refs, and cleanup.
- BioDock `current-state-feed`, `shared-feed-registry`, `valtio-stream-state`: live progress/feed state.
- BioDock `visual-ui-contracts`, `visual-legibility-verifier`, `visual-pattern-catalog`: visual contract checks.
- Rerun: synchronized temporal/MOT playback.
- FiftyOne: CV dataset and prediction inspection.
- Label Studio/CVAT: human annotation and correction.
- Datumaro: dataset export/diff/interchange.
- MLflow, DVC/DVCLive, Evidently: experiment tracking, restore, and regression reporting.

Reusable packages:
- `dq-contracts`: ids, enums, shared typed models.
- `dq-boundaries`: config and external-data validation boundaries.
- `dq-resources`: provider and resource ownership helpers.
- `dq-observability`: telemetry names and phase constants.
- `vision-columnar`: typed NumPy/Arrow memory blocks.
- `vision-geometry`: box geometry helpers.
- `mot-interfaces`: tracker protocols and contracts.
- `mot-bytetrack`: concrete ByteTrack integration.
- `dq-filter-kit`: reusable filter-stage contracts.
- `decision-ledger`: kept/merged/rejected decision records.
- `run-artifacts`: immutable run storage and indexes.
- `label-versions`: frozen label-set manifests.
- `experiment-tracking`: MLflow, DVC, Evidently export bridges.
- `experiment-runner`: bounded suite execution and state transitions.
- `evaluation-regression`: metrics, regression history, and gates.
- `visual-reporting`: report artifacts and sampled overlays.
- `platform-review`: FiftyOne and Label Studio bridges.
- `review-journey`: review surface launcher and platform manifest.
- `lineage-replay`: replay lock capture and isolated re-runs.
- `replay-workbench`: local FastAPI workbench UI.

Domain packages:
- `handdetect-domain`: hand-specific config and constants.
- `handdetect-io`: dataset-specific parsers and path scanning.
- `handdetect-policies`: hand-specific thresholds and selection policy.
- `apps/handdetect-cli`: Typer commands and app wiring only.

Do not create `vision-review-contracts`, `vision-review-artifacts`,
`biodock-generator-package`, or `biodock-vision-review-workspace` in this repository during
Phase 1. BioDock already owns the reusable workspace runtime, FlexLayout host integration,
diagnostics, hot refs, streams, C-view projection, SDK authoring surface, and visual contracts.
HandDetect may publish app-specific package descriptors and domain panels, but it must not
duplicate BioDock runtime, SDK, or layout infrastructure.
