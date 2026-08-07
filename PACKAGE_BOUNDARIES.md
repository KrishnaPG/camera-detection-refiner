# Package Boundaries

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
