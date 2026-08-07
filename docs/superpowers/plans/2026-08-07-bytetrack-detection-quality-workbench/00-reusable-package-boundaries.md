# Task 0: Reusable Package Boundary Extraction

**Files:**
- Create: `PACKAGE_BOUNDARIES.md`
- Modify: `pyproject.toml`
- Modify: `Makefile`
- Create: `packages/dq-contracts/src/dq_contracts/__init__.py`
- Create: `packages/dq-boundaries/src/dq_boundaries/__init__.py`
- Create: `packages/dq-resources/src/dq_resources/__init__.py`
- Create: `packages/dq-observability/src/dq_observability/__init__.py`
- Create: `packages/vision-columnar/src/vision_columnar/__init__.py`
- Create: `packages/vision-geometry/src/vision_geometry/__init__.py`
- Create: `packages/mot-interfaces/src/mot_interfaces/__init__.py`
- Create: `packages/mot-bytetrack/src/mot_bytetrack/__init__.py`
- Create: `packages/dq-filter-kit/src/dq_filter_kit/__init__.py`
- Create: `packages/decision-ledger/src/decision_ledger/__init__.py`
- Create: `packages/run-artifacts/src/run_artifacts/__init__.py`
- Create: `packages/label-versions/src/label_versions/__init__.py`
- Create: `packages/experiment-tracking/src/experiment_tracking/__init__.py`
- Create: `packages/experiment-runner/src/experiment_runner/__init__.py`
- Create: `packages/evaluation-regression/src/evaluation_regression/__init__.py`
- Create: `packages/visual-reporting/src/visual_reporting/__init__.py`
- Create: `packages/platform-review/src/platform_review/__init__.py`
- Create: `packages/vision-review-contracts/src/vision_review_contracts/__init__.py`
- Create: `packages/vision-review-artifacts/src/vision_review_artifacts/__init__.py`
- Create: `packages/biodock-generator-package/src/biodock_generator_package/__init__.py`
- Create: `packages/review-journey/src/review_journey/__init__.py`
- Create: `packages/lineage-replay/src/lineage_replay/__init__.py`
- Create: `packages/replay-workbench/src/replay_workbench/__init__.py`
- Create: `packages/handdetect-domain/src/handdetect_domain/__init__.py`
- Create: `packages/handdetect-io/src/handdetect_io/__init__.py`
- Create: `packages/handdetect-policies/src/handdetect_policies/__init__.py`
- Create: `apps/handdetect-cli/src/handdetect/__init__.py`
- Create: `apps/handdetect-cli/src/handdetect/cli/main.py`
- Create: `tests/drift/test_package_boundaries.py`

**Interfaces:**
- Consumes:
  - `data/README.md`.
  - `docs/hand_detection_spec.pdf`.
  - `docs/coding-plan-standards.md`.
  - `docs/coding-standards.md`.
  - Plan files `01` through `09`.
- Produces:
  - `PACKAGE_BOUNDARIES.md` as the authoritative reusable package map.
  - One package per reusable ownership boundary.
  - A thin `apps/handdetect-cli` package for CLI commands and app-specific wiring only.
  - Drift guard `tests/drift/test_package_boundaries.py`.

## Reuse-First Rule

Before creating any new package listed in this task, the implementer must prove that the
capability is not already owned by either:

1. an existing BioDock reusable package under `external/biodock/frontend/packages/`, or
2. a mature permissive open-source project already selected in the implementation plan.

If an existing package is close enough, extend it behind its existing ownership boundary. Do not
create a parallel HandDetect package with a different state model, layout model, viewer adapter,
manifest format, or platform bridge.

## Existing Reuse Inventory

| Capability | Existing owner | Decision |
|---|---|---|
| Generator package descriptors, semantic panel runtime, actions, selectors, evidence | `@biodock-labs/generator-workspace-runtime` | Reuse directly. Do not create a HandDetect runtime. |
| FlexLayout compilation from package slots and base layouts | `@biodock-labs/generator-workspace-host-adapters`, `@biodock-labs/flexlayout-topology-adapter` | Extend only to add `berg10.generator.videoReview`; do not hand-author FlexLayout JSON in HandDetect. |
| BioDock panel hosting and workspace chrome | `@biodock-labs/scientific-workspace`, `@biodock-labs/generator-workspace-react` | Reuse directly for story-page hosting. |
| Panel artifacts and viewer adapter manifests | `@biodock-labs/artifact-viewer-adapter-registry`, `@biodock-labs/static-artifact-descriptor-cache` | Reuse/extend adapter registrations only. |
| Browser diagnostics and visible proof | `@biodock-labs/browser-diagnostics`, `@biodock-labs/presentation-readiness-state` | Reuse directly for frame budget, sync drift, missing assets, and story-readiness status. |
| Hot viewer state and lifecycle cleanup | `@biodock-labs/viewer-hot-state-refs`, `@biodock-labs/lifecycle-leases` | Reuse directly for video/canvas refs, animation frames, and cleanup. |
| Long-lived streams and keyed feed state | `@biodock-labs/current-state-feed`, `@biodock-labs/shared-feed-registry`, `@biodock-labs/valtio-stream-state`, `@biodock-labs/eventsource-feed-session` | Reuse directly if live progress/events are streamed into panels. |
| Query keys and selector safety | `@biodock-labs/query-key-factory`, `@biodock-labs/react-external-store-selectors` | Reuse directly; no ad-hoc query-key arrays or broad snapshots. |
| Visual contracts and legibility checks | `@biodock-labs/visual-ui-contracts`, `@biodock-labs/visual-legibility-verifier`, `@biodock-labs/visual-pattern-catalog` | Reuse for visual-quality gates against the mock. |
| Berg10 C-view/Arrow data projection | `@biodock-labs/berg10-columnar-store`, `@biodock-labs/berg10-cview-arrow-stream`, `@biodock-labs/berg10-cview-react` | Reuse for run rows/artifact views; do not build a separate browser data plane. |
| Temporal multimodal MOT/video inspection | Rerun, MIT OR Apache-2.0 | Use for deep synchronized playback and MOT debugging; do not duplicate its full viewer. |
| Visual CV dataset inspection/filtering | FiftyOne, Apache-2.0 | Use for dataset/sample/prediction review and filtering; do not recreate a dataset browser. |
| Human video/image annotation | CVAT Community, MIT; Label Studio through configured service/SDK | Phase 1 uses Label Studio handoff; Phase 2 uses CVAT for video correction. Do not implement custom annotation UI. |
| Dataset import/export/diff | Datumaro, MIT | Use in Phase 2; do not build bespoke converters/diff tools. |
| Experiment tracking and regressions | MLflow, DVC/DVCLive, Evidently | Use for run comparison, metric history, exact restore, and reports/workspace links. |
| Low-level timeline widget | `react-timeline-editor`, MIT, only if BioDock/Rerun cannot cover the interaction | Allowed as a component inside a BioDock panel, not as a new app/runtime. |
| Full browser video editor kits | OpenVideo/RVE-style projects have mixed or commercial licensing | Do not adopt without a license review; the product needs review/playback, not editing/export authoring. |

## Fixed-Point Reusable Pattern Extraction

- Round 1 reusable primitives found in the requirements:
  - `dq-contracts`:
    - Owns branded ids, enum contracts, error-code enums, model base conventions, and typed
      status values.
    - Reusable because every detector-quality, evaluation, and replay system needs domain-safe
      identities and state values.
    - Must never read files, call network, run algorithms, or import hand-specific code.
  - `dq-boundaries`:
    - Owns Raw/Untrusted to Validated parsing, Pydantic v2 boundary calls, canonical TOML/JSON
      serialization, and config hash computation.
    - Reusable because every project has untrusted JSON/config/manifest/label inputs.
    - Must never own detector policy or persistence.
  - `dq-resources`:
    - Owns ready handles, provider injection, resource path builders, subprocess command
      runner, clocks, id providers, and ExitStack ownership helpers.
    - Reusable because every workflow needs valid-if-created resources and deterministic
      replay boundaries.
    - Must never know clip schema, labels, metrics, or hand rules.
  - `dq-observability`:
    - Owns metric names, log keys, OTel phase constants, telemetry handles, and non-blocking
      exporter status.
    - Reusable because every package must emit consistent phase-level telemetry.
    - Must never own domain decisions or hot-path payloads.
  - `vision-columnar`:
    - Owns zero-copy NumPy/Arrow detection blocks, track blocks, decision blocks, schema
      builders, scratch buffers, and Parquet table schemas.
    - Reusable because detector outputs across object classes can use the same box, score,
      frame, timestamp, and track memory shapes.
    - Must never parse assignment JSON or choose false-positive policy.
  - `vision-geometry`:
    - Owns XYXY box primitives, IoU, area/aspect helpers, overlap grouping, border proximity,
      and vectorized frame geometry.
    - Reusable because size, shape, overlap, border, and movement gates recur across visual
      adapter projects.
    - Must never own object-specific thresholds.
  - `mot-interfaces`:
    - Owns tracker protocols, native input/output shapes, track lifecycle events, and tracker
      adapter contracts.
    - Reusable because ByteTrack, OC-SORT, SORT, and other MOT libraries can share the same
      interface.
    - Must never import a concrete tracker library.
  - `decision-ledger`:
    - Owns kept/merged/rejected/interpolated decision schemas, audit JSONL writers, reason
      registries, and provenance row schemas.
    - Reusable because any post-detector adapter needs a non-optional record of changes.
    - Must never decide whether a detection should be rejected.
  - `run-artifacts`:
    - Owns immutable run roots, manifest writing, atomic file writes, append-only run indexes,
      metric-history indexes, file locks, and cleanup by run id.
    - Reusable because every experiment suite needs non-overwriting outputs and queryable
      history.
    - Must never compute vision metrics or call MLflow/DVC directly.
  - `label-versions`:
    - Owns immutable label-set manifests, canonical annotation exports, label-set id hashing,
      and DVC add hooks for reviewed labels.
    - Reusable because gold labels must be versioned independently of hand detection.
    - Must never compute adapter metrics.
  - `experiment-tracking`:
    - Owns MLflow, DVC/DVCLive, and Evidently adapters plus platform export status.
    - Reusable because experiment parameter/metric/report export is not hand-specific.
    - Must never own run execution or visual review.
  - `platform-review`:
    - Owns FiftyOne dataset publishing, Label Studio task/project import, review platform
      statuses, and platform URL/path manifests.
    - Reusable because visual CV review and annotation correction recur across projects.
    - Must never implement custom annotation editing or run comparison.
  - `vision-review-contracts`:
    - Owns only backend/browser artifact contracts that BioDock and external tools consume:
      story manifests, clip timeline/event/track/chapter schemas, panel ids, layer ids,
      support states, and platform-link contracts.
    - Reusable because many CV adapters need a compact browser-review artifact contract.
    - Must not own React state, FlexLayout topology, viewer lifecycle, or BioDock runtime logic;
      those are already owned by BioDock packages.

- Round 2 reusable composites built from Round 1:
  - `mot-bytetrack`:
    - Composes `mot-interfaces`, `vision-columnar`, and `dq-resources`.
    - Owns `trackers==2.6.0` ByteTrack integration and reusable tracker tensor scratch buffers.
    - Must never encode hand-specific max-two or exit-path policy.
  - `dq-filter-kit`:
    - Composes `dq-contracts`, `vision-columnar`, `vision-geometry`, and `decision-ledger`.
    - Owns filter strategy protocols, filter registries, stage results, and generic size,
      shape, duplicate, displacement, flicker, and static-detection strategy hooks.
    - Must never hardcode hand thresholds or hand count.
  - `experiment-runner`:
    - Composes `dq-boundaries`, `dq-resources`, `dq-observability`, `run-artifacts`,
      and `experiment-tracking`.
    - Owns suite state machines, bounded clip-worker orchestration, matrix expansion, and
      run completion status.
    - Must never parse WiLoR/ZED/VIO files or implement detector-quality filters.
  - `evaluation-regression`:
    - Composes `label-versions`, `vision-geometry`, `vision-columnar`, `run-artifacts`,
      and `experiment-tracking`.
    - Owns IoU matching, precision/recall guardrails, per-stage metric deltas, metric-history
      scans, and regression gate results.
    - Must never own review UI or detector-specific policy.
  - `visual-reporting`:
    - Composes `vision-columnar`, `decision-ledger`, `run-artifacts`, and Supervision/OpenCV
      annotation helpers.
    - Owns sampled frame manifests, overlays, contact sheets, and static report fragments.
    - Must never run adapter logic or decide whether a detection is valid.
  - `vision-review-artifacts`:
    - Composes `vision-review-contracts`, `vision-columnar`, `decision-ledger`,
      `run-artifacts`, `visual-reporting`, Rerun export hooks, and open-source video/image
      tooling.
    - Owns compact artifact projection only: timeline/event/track JSON, chapter extraction,
      overlay video generation, thumbnail strips, and Rerun recording manifests.
    - Must not implement a timeline UI, custom dataset browser, custom annotation editor, or
      video-editor runtime. BioDock, Rerun, FiftyOne, Label Studio, and CVAT own those.
  - `biodock-generator-package`:
    - Composes `vision-review-contracts`, `review-journey`, `run-artifacts`, and BioDock
      Generator Package descriptor/view/theme files.
    - Owns package artifact publication and compatibility checks for `handdetect-quality-adapter`.
    - Must not duplicate `generator-workspace-runtime`, `generator-workspace-host-adapters`,
      `scientific-workspace`, or `flexlayout-topology-adapter`; changes needed there must be
      upstreamed or pinned in BioDock.
  - `review-journey`:
    - Composes `experiment-tracking`, `platform-review`, `visual-reporting`, and
      `run-artifacts`.
    - Owns the one-command platform hub manifest and platform opening/URL reporting.
    - Must never duplicate MLflow/DVC/Evidently/FiftyOne/Label Studio UI features.
  - `lineage-replay`:
    - Composes `dq-resources`, `dq-boundaries`, `run-artifacts`, `label-versions`, and
      `experiment-runner`.
    - Owns replay locks, DVC/Git refs, isolated worktrees, typed config overrides, child-run
      creation, and parent regression comparison.
    - Must never become a custom artifact database.

- Round 3 reusable product shells built from Round 2:
  - `replay-workbench`:
    - Composes `lineage-replay`, `review-journey`, `evaluation-regression`, and FastAPI.
    - Owns only fallback local orchestration for run detail, lineage proof, typed overrides,
      replay status, and platform links when BioDock is unavailable.
    - Must never implement custom charts, annotation screens, video browsers, or the primary
      story page.
  - `biodock-vision-review-workspace` is not created as a new package in this repository:
    - Existing BioDock packages already own workspace runtime, FlexLayout host integration,
      C-view projection, diagnostics, and viewer lifecycle.
    - Required implementation is an extension to BioDock base layouts plus HandDetect package
      descriptors/panels, not a parallel workbench package.
  - `detector-quality-workbench` remains a conceptual composition, not a package in this
    delivery:
    - It would compose `experiment-runner`, `dq-filter-kit`, `mot-interfaces`,
      `evaluation-regression`, `review-journey`, `lineage-replay`, `replay-workbench`, and
      `biodock-generator-package`.
    - It is not created as a package now because BioDock provides the reusable host and the
      hand-specific app is the only concrete backend consumer in this repository.

- Round 4 fixed-point result:
  - No further reusable packages are extracted after `replay-workbench` and
    `biodock-generator-package`.
  - Remaining modules are business/domain-specific because they depend on this assignment's
    ZED/WiLoR/VIO layout or hand-specific behavior.
  - Domain-specific packages:
    - `handdetect-domain` owns hand-specific constants, policy ids, hand adapter config, and
      hand report vocabulary.
    - `handdetect-io` owns this dataset's `frame_ts.json`, `hand_boxes.json`, `vio_pose.json`,
      `meta.json`, ZED left/right video path conventions, and WiLoR detector metadata.
    - `handdetect-policies` owns hand-specific duplicate/size/shape/displacement/static
      thresholds, max-two wearer-hand selection, lower-border exit assumptions, and the
      first-delivery rule that interpolation count is always zero.
    - `apps/handdetect-cli` owns Typer commands, app config presets, Makefile-visible commands,
      and app-specific wiring. It may re-export reusable types for CLI ergonomics but must not
      contain reusable implementation logic.

## Final Package List

- Reusable packages:
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
  - `vision-review-contracts`
  - `vision-review-artifacts`
  - `biodock-generator-package`
  - `review-journey`
  - `lineage-replay`
  - `replay-workbench`
- Domain/business packages:
  - `handdetect-domain`
  - `handdetect-io`
  - `handdetect-policies`
  - `apps/handdetect-cli`

## Normative Path Map For Existing Tasks

- Existing task snippets that reference `src/handdetect/domain` must implement reusable parts in
  `packages/dq-contracts` and hand-specific constants in `packages/handdetect-domain`.
- Existing task snippets that reference `src/handdetect/config` must implement parser and
  canonicalization primitives in `packages/dq-boundaries`.
- Existing task snippets that reference `src/handdetect/observability` must implement telemetry
  contracts in `packages/dq-observability`.
- Existing task snippets that reference `src/handdetect/io` must implement assignment-specific
  parsers in `packages/handdetect-io`; generic parser helpers belong in `packages/dq-boundaries`.
- Existing task snippets that reference `src/handdetect/hotpath` must implement native memory
  layout in `packages/vision-columnar`.
- Existing task snippets that reference `src/handdetect/filters` must implement registry and
  reusable filters in `packages/dq-filter-kit`; hand thresholds and max-two policy belong in
  `packages/handdetect-policies`.
- Existing task snippets that reference `src/handdetect/tracking/interfaces` must implement
  tracker protocols in `packages/mot-interfaces`.
- Existing task snippets that reference `src/handdetect/tracking/bytetrack.py` must implement the
  concrete adapter in `packages/mot-bytetrack`.
- Existing task snippets that reference `src/handdetect/audit` must implement decision artifacts
  in `packages/decision-ledger`.
- Existing task snippets that reference `src/handdetect/runs` must implement run storage in
  `packages/run-artifacts`.
- Existing task snippets that reference `src/handdetect/eval` or `src/handdetect/regression` must
  implement generic metrics and gates in `packages/evaluation-regression`.
- Existing task snippets that reference `src/handdetect/report` must implement reusable visual
  report builders in `packages/visual-reporting` and hand-specific copy in `handdetect-domain`.
- Existing task snippets that reference `src/handdetect/review` must implement platform bridges in
  `packages/platform-review`, compact story artifact contracts in
  `packages/vision-review-contracts`, artifact projection in `packages/vision-review-artifacts`,
  and BioDock package publication in `packages/biodock-generator-package`.
- Existing task snippets that reference `src/handdetect/tracking_platforms` must implement exports
  in `packages/experiment-tracking`.
- Existing task snippets that reference `src/handdetect/experiments` or `src/handdetect/pipeline`
  must implement generic orchestration in `packages/experiment-runner`.
- Existing task snippets that reference `src/handdetect/review_journey` must implement hub
  orchestration in `packages/review-journey`.
- Existing task snippets that reference `src/handdetect/labels` or `src/handdetect/lineage` must
  implement generic label freezing and replay in `packages/label-versions` and
  `packages/lineage-replay`.
- Existing task snippets that reference `src/handdetect/workbench` must implement the local UI in
  `packages/replay-workbench` only as fallback orchestration. The primary story UI must use
  BioDock Generator Package panels and existing BioDock frontend packages.
- Existing task snippets that reference `src/handdetect/cli` must implement only app command
  wiring in `apps/handdetect-cli`.

## Implementation Guard

- Reusable package code must not import `handdetect_domain`, `handdetect_io`,
  `handdetect_policies`, or `handdetect`.
- Domain packages may import reusable packages.
- `apps/handdetect-cli` may import all packages, but must not implement algorithms, storage,
  parsing, tracking, label freezing, replay, review bridges, or metrics.
- A duplicate second implementation of any reusable pattern inside `apps/handdetect-cli` or a
  hand-specific package is a plan violation.
- A duplicate second implementation of BioDock-owned runtime, FlexLayout compilation, workspace
  chrome, diagnostics, hot refs, stream/session state, or visual contract verification is a plan
  violation.

- [ ] **Step 1: Write package-boundary drift guard**

Create `tests/drift/test_package_boundaries.py`:

```python
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "apps" / "handdetect-cli" / "src" / "handdetect"
REUSABLE_IMPORT_PREFIXES = (
    "dq_",
    "vision_",
    "mot_",
    "decision_ledger",
    "run_artifacts",
    "label_versions",
    "experiment_",
    "evaluation_regression",
    "visual_reporting",
    "platform_review",
    "vision_review_contracts",
    "vision_review_artifacts",
    "biodock_generator_package",
    "review_journey",
    "lineage_replay",
    "replay_workbench",
)


def test_app_package_contains_only_cli_wiring() -> None:
    allowed = {APP_ROOT / "__init__.py", APP_ROOT / "cli" / "main.py"}
    files = {path for path in APP_ROOT.rglob("*.py")}
    assert files <= allowed


def test_reusable_packages_do_not_import_handdetect_domains() -> None:
    package_root = ROOT / "packages"
    forbidden = ("handdetect", "handdetect_domain", "handdetect_io", "handdetect_policies")
    for path in package_root.rglob("*.py"):
        if path.parts[-3].startswith("handdetect-"):
            continue
        text = path.read_text(encoding="utf-8")
        for name in forbidden:
            assert f"import {name}" not in text
            assert f"from {name}" not in text


def test_handdetect_domain_packages_import_reusable_packages_for_shared_logic() -> None:
    domain_roots = [
        ROOT / "packages" / "handdetect-domain" / "src",
        ROOT / "packages" / "handdetect-io" / "src",
        ROOT / "packages" / "handdetect-policies" / "src",
    ]
    joined = "\n".join(path.read_text(encoding="utf-8") for root in domain_roots for path in root.rglob("*.py"))
    assert any(f"import {prefix}" in joined or f"from {prefix}" in joined for prefix in REUSABLE_IMPORT_PREFIXES)
```

- [ ] **Step 2: Create package boundary document**

Create `PACKAGE_BOUNDARIES.md` by copying the sections:

- `Reuse-First Rule`
- `Existing Reuse Inventory`
- `Fixed-Point Reusable Pattern Extraction`
- `Final Package List`
- `Normative Path Map For Existing Tasks`
- `Implementation Guard`

from this task file.

- [ ] **Step 3: Create package directories**

Run:

```bash
mkdir -p packages/dq-contracts/src/dq_contracts
mkdir -p packages/dq-boundaries/src/dq_boundaries
mkdir -p packages/dq-resources/src/dq_resources
mkdir -p packages/dq-observability/src/dq_observability
mkdir -p packages/vision-columnar/src/vision_columnar
mkdir -p packages/vision-geometry/src/vision_geometry
mkdir -p packages/mot-interfaces/src/mot_interfaces
mkdir -p packages/mot-bytetrack/src/mot_bytetrack
mkdir -p packages/dq-filter-kit/src/dq_filter_kit
mkdir -p packages/decision-ledger/src/decision_ledger
mkdir -p packages/run-artifacts/src/run_artifacts
mkdir -p packages/label-versions/src/label_versions
mkdir -p packages/experiment-tracking/src/experiment_tracking
mkdir -p packages/experiment-runner/src/experiment_runner
mkdir -p packages/evaluation-regression/src/evaluation_regression
mkdir -p packages/visual-reporting/src/visual_reporting
mkdir -p packages/platform-review/src/platform_review
mkdir -p packages/vision-review-contracts/src/vision_review_contracts
mkdir -p packages/vision-review-artifacts/src/vision_review_artifacts
mkdir -p packages/biodock-generator-package/src/biodock_generator_package
mkdir -p packages/review-journey/src/review_journey
mkdir -p packages/lineage-replay/src/lineage_replay
mkdir -p packages/replay-workbench/src/replay_workbench
mkdir -p packages/handdetect-domain/src/handdetect_domain
mkdir -p packages/handdetect-io/src/handdetect_io
mkdir -p packages/handdetect-policies/src/handdetect_policies
mkdir -p apps/handdetect-cli/src/handdetect/cli
```

Create one empty `__init__.py` in each package directory.

- [ ] **Step 4: Run drift guard**

Run:

```bash
python -m pytest tests/drift/test_package_boundaries.py -v
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit package boundary setup**

Commit:

```bash
git add PACKAGE_BOUNDARIES.md packages apps tests/drift/test_package_boundaries.py
git commit -m "chore: add reusable package boundaries"
```
