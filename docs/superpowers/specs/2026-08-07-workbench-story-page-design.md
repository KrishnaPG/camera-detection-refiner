# Workbench Story Page Design

Date: 2026-08-07
Status: Design blocker for Phase 1

## Saved Work Items

Phase 1 goal:
Build the visual review journey that makes a run demonstrable from the Workbench: story page, full-clip visual outputs, Rerun export, richer FiftyOne export, MLflow deep links, and edge-case tags.

Current blocker:
Finalize the Workbench story page feature set, information architecture, and mock UI design before implementation starts.

Phase 2 goal:
Integrate CVAT for video correction, Datumaro for dataset export/diff/interchange, and Evidently workspace UI for evaluation history.

## Product Intent

The story page must let an evaluator or customer understand the adapter without reading tables or CLI output. The page must answer five questions visually:

1. What was the full input clip?
2. What did the detector report on each frame?
3. What did the adapter approve, merge, or reject?
4. Which ByteTrack MOT tracks explain the temporal decisions?
5. Which hand-detection spec edge cases are visible, handled, candidate-only, or unsupported?

The default experience should feel closer to a professional video editor or VFX review bay than to a metrics dashboard. Metrics are still present, but the primary object is time: a clip, a playhead, tracks, frame evidence, and decision events.

## Non-Negotiable Requirements

- The story page must open from a run detail page with one click.
- The first viewport must show the clip review surface, not a report landing page.
- The page must support all clips in the run, not only sampled stills.
- The raw input video, raw detector overlays, adapter output overlays, rejected/merged overlays, and track overlays must stay frame-synchronized.
- The bottom timeline must be zoomable and must show frame ticks, MOT track lanes, rejection markers, and a minimap for the whole clip.
- The user must be able to jump to the next or previous adapter decision event.
- The user must be able to isolate a track and dim all other detections.
- Rejection categories must be visible as customer-readable classifications, not just enum strings.
- Every visible box must be inspectable down to detection id, frame index, timestamp, confidence, track id, stage, reason, and final decision.
- The page must show which spec edge cases are implemented, which are heuristic candidates, and which are not supported by the current data or Phase 1 scope.
- The page must link to the exact MLflow run and matching platform artifacts for the same run.
- The page must not require users to remember CLI commands or manually map suite/run ids to platform ids.
- The page must degrade visibly when an artifact is missing and must explain the missing artifact and remediation.

## Data Model

The story page consumes review-optimized artifacts derived from the existing authoritative run tables. Parquet remains the audit source; frontend assets are projections.

Required Phase 1 artifacts:

- `review/story.json`
  - Run identity, artifact links, platform deep links, clip summaries, available layouts, and feature support states.
- `review/clips/<clip_id>/timeline.json`
  - Compact frame/event index for browser load. Contains frame count, fps, timeline ticks, event markers, track lanes, and chapter ids.
- `review/clips/<clip_id>/events.json`
  - Decision events grouped by frame and event id. Contains detection id, decision, stage, reason, track id, confidence, severity, and display label.
- `review/clips/<clip_id>/tracks.json`
  - Track lifecycles, color ids, start/end frames, duration, kept/rejected counts, average confidence, and discontinuity markers.
- `review/clips/<clip_id>/chapters.json`
  - Demo chapters such as duplicate merge, unsupported flicker, implausible shape, stable retained track, and max-two selection.
- `review/clips/<clip_id>/raw_overlay.mp4`
  - Input video with raw detector boxes.
- `review/clips/<clip_id>/adapter_overlay.mp4`
  - Input video with final kept hands and track ids.
- `review/clips/<clip_id>/rejected_overlay.mp4`
  - Input video with rejected and merged detections labeled by rejection category.
- `review/clips/<clip_id>/compare_raw_adapter.mp4`
  - Side-by-side raw-vs-adapter composite for customer demo mode.
- `review/clips/<clip_id>/thumbnail_strip.webp`
  - Fixed-step visual strip for the minimap and timeline zoom context.

Frame-level data must be compact. The browser must not load raw Parquet or full audit JSONL for normal playback. Debug panels may link to source tables through Workbench artifact routes.

## Edge-Case Taxonomy

Each edge-case tag must carry a support state:

- `implemented_rejection`: adapter applies a concrete rejection or merge rule.
- `implemented_tracking_signal`: adapter produces useful MOT evidence but does not make a separate rejection from that tag.
- `heuristic_candidate`: artifact generator can surface likely examples, but this is not an accuracy claim.
- `not_supported`: current scope or data lacks the needed signal.

Required tags:

- `duplicate_boxes_on_one_hand`: `implemented_rejection`
- `implausible_size`: `implemented_rejection`
- `implausible_shape`: `implemented_rejection`
- `implausible_displacement`: `implemented_rejection`
- `unsupported_detection`: `implemented_rejection`
- `static_detection`: `implemented_rejection`
- `max_two_selection`: `implemented_rejection`
- `hand_exit_side_border`: `heuristic_candidate`
- `hand_exit_lower_border`: `heuristic_candidate`
- `brief_occlusion_candidate`: `heuristic_candidate`
- `hands_cross_or_overlap_candidate`: `heuristic_candidate`
- `long_absence_reentry_candidate`: `heuristic_candidate`
- `motion_blur_dropout_candidate`: `heuristic_candidate`
- `possible_bystander_hand`: `not_supported` until stereo-depth calibration/depth extraction is implemented.
- `gloved_or_partially_occluded_hand`: `not_supported` until labeled examples exist.
- `false_negative_interpolation`: `not_supported` in this assignment delivery.

The UI must never present heuristic or unsupported tags as proven correctness.

## Reusable Frontend Packages

The story page should reuse or mirror the following package patterns from `external/biodock/frontend/packages/`:

- `flexlayout-topology-adapter`
  - Use its slot-topology pattern to create deterministic FlexLayout JSON presets.
  - Do not mirror FlexLayout visibility state in Valtio.
- `scientific-workspace`
  - Reuse the workspace-shell concepts: panel registry, layout presets, toolbar/status bar, persistence, selection/brush channels, and panel error boundary.
- `ui-chrome-state`
  - Reuse the coarse activity/surface/observability state shape for story-page chrome.
- `viewer-hot-state-refs`
  - Use the hot-ref pattern for video elements, canvas contexts, animation frames, and playhead internals.
- `artifact-viewer-adapter-registry`
  - Reuse the capability-manifest pattern for story-page viewer adapters: video, overlay canvas, timeline, Rerun link, source table link.
- `browser-diagnostics`
  - Reuse scalar diagnostics for frame-budget, first usable story paint, clip asset load time, video sync drift, and proof observations.
- `scientific-presentation-controls`
  - Reuse panel-local presentation control contracts for layer toggles, story snapshots, and layout mode.
- `lifecycle-leases`
  - Use for video/canvas listener cleanup and timeline subscription ownership.

New hand-detection-specific frontend packages may be added only when these generic packages do not fit. The expected new packages are:

- `vision-review-contracts`
  - Strongly typed story manifest, clip timeline, event, track, chapter, layer, and support-state contracts.
- `vision-review-workspace`
  - Workbench story shell and FlexLayout presets.
- `vision-video-reviewer`
  - Synchronized video/canvas playback, layer control, and frame stepping.
- `vision-timeline-reviewer`
  - Zoomable timeline, track lanes, markers, minimap, brushing, and playhead synchronization.

## Panel Inventory

### Clip Navigator

Purpose:
Choose clip, chapter, edge-case group, or strongest demo moment.

Must show:
- Clip id and task label.
- Duration, frame count, raw count, kept count, rejected count.
- Badges for available edge cases.
- A "strongest examples" section ranked by visual explanatory value.

### Story Header

Purpose:
Make the run sellable in one sentence and traceable in one click.

Must show:
- Run suite id, run id, experiment id.
- Outcome strip: raw detections, kept detections, rejected/merged detections, false-positive delta, interpolation count.
- Exact links: MLflow run, Rerun recording, FiftyOne view, Label Studio/CVAT handoff, replay lock.
- Support warning strip for unsupported edge cases.

### Synchronized Viewer

Purpose:
Primary visual evidence.

Modes:
- `compare`: left raw detector, right adapter output.
- `forensic`: input, raw, kept, rejected in a 2x2 grid.
- `single`: one large viewer with layer toggles.
- `presentation`: full-bleed composite with minimal chrome.

Must support:
- Play, pause, speed, previous/next frame, previous/next event.
- Layer toggles.
- Track isolation.
- Box hover and click.
- Frame-exact playhead publication.
- Canvas overlay alignment verification.

### Timeline

Purpose:
Make temporal behavior inspectable.

Must show:
- Playhead.
- Frame ticks.
- Zoom range.
- Minimap.
- Thumbnail strip.
- Track lanes.
- Rejection markers.
- Duplicate merge markers.
- Event density heatmap.
- Selected loop range.

Must support:
- Wheel or slider zoom.
- Drag to scrub.
- Shift-drag to select range.
- Click marker to select event.
- Jump controls.

### Decision Inspector

Purpose:
Explain what happened on the selected frame/event.

Must show:
- Detection id.
- Frame index and timestamp.
- Raw coordinates.
- Confidence.
- Detector handedness with reliability note.
- Decision: kept, rejected, merged.
- Stage and reason.
- Track id, age, score.
- Merged-into detection id when present.
- Customer-readable explanation.
- Link to source audit row or table slice.

### Rejection Taxonomy

Purpose:
Turn false-positive handling into a visual feature.

Must show:
- Duplicate detections.
- Implausible size.
- Implausible shape.
- Implausible displacement.
- Unsupported detection.
- Static detection.
- Max-two selection.
- Count and percentage per group.
- Jump-to-examples action per group.
- Implemented/heuristic/not-supported state.

### Track Explorer

Purpose:
Make ByteTrack MOT tangible.

Must show:
- Track id.
- Color swatch.
- Start/end frame.
- Duration.
- Kept/rejected count.
- Average confidence.
- Discontinuities or switches.
- "Isolate track" action.
- "Show raw flicker vs adapter continuity" action.

### Metrics And Regression

Purpose:
Keep quantitative proof available without dominating the page.

Must show:
- Per-clip counts.
- Per-stage deltas.
- Over-cap frame count.
- Frames changed by adapter.
- Regression status.
- MLflow exact run link.
- Evidently artifact or workspace link.

### Platform Bridge

Purpose:
Make external tools feel like part of one journey.

Must show:
- Rerun recording link for the selected clip.
- FiftyOne dataset/view link filtered to selected clip or frame when possible.
- Label Studio task link for Phase 1 image review.
- CVAT task link once Phase 2 is implemented.
- Datumaro export path once Phase 2 is implemented.
- Status per platform: ready, degraded, missing, unsupported.

## Default Layout: Customer Demo Console

This is the recommended first implementation and the default layout.

```
+------------------------------------------------------------------------------------------------+
| Story Header: Run outcome, support state, exact platform links                                  |
+------------------------+--------------------------------------------------+--------------------+
| Clip Navigator         | Synchronized Viewer                              | Decision Inspector |
| - Clips                | [Raw Detector]        [Adapter Output]           | - selected event   |
| - Strong examples      | frame-locked video comparison                    | - why changed      |
| - Chapters             | layer toggles over viewer footer                 | - source evidence  |
| - Edge cases           |                                                  |                    |
+------------------------+--------------------------------------------------+--------------------+
| Timeline: minimap, thumbnail strip, track lanes, rejection markers, zoomable frame ruler         |
+------------------------------------------------------------------------------------------------+
| Status Bar: asset freshness, video sync drift, frame budget, export status                      |
+------------------------------------------------------------------------------------------------+
```

Why this layout:
- A customer sees the value immediately: raw detector on one side, adapter output on the other.
- The bottom timeline proves the work is temporal, not cherry-picked stills.
- The right inspector explains decisions without making the viewer leave the video.
- The left navigator supports a guided sales/demo story.

Visual direction:
- Dark-neutral editor surface with high-contrast overlays.
- Green for kept, red for rejected, amber for merged, cyan/violet stable track colors.
- Thin chrome, dense professional controls, no marketing hero.
- Event markers are more saturated than metric panels.
- Text is compact and never placed over important video content except box labels.

## Layout Preset: Forensic Review Bay

```
+------------------------------------------------------------------------------------------------+
| Story Header                                                                                   |
+----------------------+----------------------------+----------------------------+--------------+
| Filters + Layers     | Input Video                | Raw Detector               | Track Explorer|
| Rejection Taxonomy   +----------------------------+----------------------------+              |
|                      | Kept Output                | Rejected/Merged            |              |
+----------------------+----------------------------+----------------------------+--------------+
| Timeline                                                                                       |
+------------------------------------------------------------------------------------------------+
| Decision Inspector + Source Table Slice                                                        |
+------------------------------------------------------------------------------------------------+
```

Purpose:
Engineering review and debugging. This layout sacrifices presentation simplicity for full visibility into every intermediate artifact.

## Layout Preset: Annotation Handoff

```
+------------------------------------------------------------------------------------------------+
| Story Header + Label/Review State                                                              |
+----------------------+-----------------------------------------------------+-------------------+
| Rejection Queue      | Adapter Output + Rejected Overlay                   | Correction Packet |
| Edge-Case Groups     | selected frame/range                                | - send to CVAT    |
|                      |                                                     | - export packet   |
+----------------------+-----------------------------------------------------+-------------------+
| Range Timeline: selected frames, tasks, comments, review packets                                |
+------------------------------------------------------------------------------------------------+
| Platform Bridge: Label Studio, CVAT, Datumaro, FiftyOne, Rerun                                  |
+------------------------------------------------------------------------------------------------+
```

Purpose:
Human correction workflow. Phase 1 can show Label Studio handoff; Phase 2 adds CVAT and Datumaro actions.

## Layout Preset: Metrics And Regression

```
+------------------------------------------------------------------------------------------------+
| Story Header                                                                                   |
+-------------------------+---------------------------------------+--------------------------------+
| Run/Lineage Panel       | Counts and Stage Deltas                | Regression and Baseline         |
| MLflow exact run        | Per-clip table                         | Evidently workspace/report      |
+-------------------------+---------------------------------------+--------------------------------+
| Timeline + Changed Frames                                                                       |
+------------------------------------------------------------------------------------------------+
| Visual Examples Strip                                                                           |
+------------------------------------------------------------------------------------------------+
```

Purpose:
Experiment comparison, replay review, and regression discussion. This layout is secondary because it should not replace visual proof.

## FlexLayout Model Strategy

Use a slot-topology model instead of hand-authored nested JSON in application code.

Slot ids:
- `slot.story.header`
- `slot.clip.navigator`
- `slot.viewer.primary`
- `slot.inspector`
- `slot.timeline`
- `slot.status`
- `slot.taxonomy`
- `slot.track.explorer`
- `slot.metrics`
- `slot.platforms`

Panel component ids:
- `StoryHeaderPanel`
- `ClipNavigatorPanel`
- `SynchronizedViewerPanel`
- `TimelinePanel`
- `DecisionInspectorPanel`
- `RejectionTaxonomyPanel`
- `TrackExplorerPanel`
- `MetricsRegressionPanel`
- `PlatformBridgePanel`
- `StatusBarPanel`

FlexLayout owns tab selection, visibility, dock state, maximize, and serialized layout JSON. Story-page state stores only the active clip, playhead, selected event, selected track, selected layer set, selected layout preset, and coarse loading/error statuses.

## State And Synchronization

Canonical UI state:

- `activeClipId`
- `playheadFrame`
- `playbackState`
- `playbackRate`
- `selectedEventId`
- `selectedTrackId`
- `visibleLayers`
- `loopRange`
- `timelineZoom`
- `activeLayoutPreset`
- `platformStatuses`

Hot non-render-driving state:

- HTML video element refs.
- Canvas refs.
- Animation frame handle.
- Last decoded video time.
- Last overlay draw frame.
- Pointer hover frame.
- Frame-to-pixel scale cache.

Rules:
- React state and Valtio snapshots must not update every frame during playback.
- A playback adapter owns synchronization and publishes coarse render state at bounded cadence or on discrete events.
- Timeline canvas draws from immutable event arrays and hot playhead refs.
- Selecting an event updates render-driving state because it changes inspector content.

## Visual Design System

Palette:
- Background: near-black editor neutral.
- Viewer chrome: charcoal with subtle borders.
- Kept boxes: green.
- Rejected boxes: red.
- Merged boxes: amber.
- Raw boxes: blue.
- Track colors: rotating high-contrast cyan, violet, lime, orange, magenta.
- Unsupported state: gray with striped marker.
- Heuristic candidate: purple outline with dotted marker.

Typography:
- Compact interface scale.
- Monospace only for ids, hashes, timestamps, frame numbers, and exact artifact paths.
- No viewport-width font scaling.
- No negative letter spacing.

Controls:
- Icon buttons for play, pause, previous frame, next frame, jump event, layer visibility, maximize, export, and open platform.
- Segmented controls for viewer mode and layout preset.
- Toggles for layers.
- Slider/number input for timeline zoom.
- Menu for playback rate.
- Tooltips for non-obvious icons.

## User Journey

1. User runs a smoke experiment.
2. Workbench run detail shows a primary button: `Open Story Review`.
3. Story page opens in Customer Demo Console layout.
4. The page selects the strongest example chapter automatically.
5. User presses play and sees raw detector boxes over-firing while adapter output remains stable.
6. User clicks a red rejection marker.
7. Playback jumps to that frame. The inspector explains the decision and shows the detection id, stage, reason, track id, and source evidence.
8. User toggles `Rejected` and `Merged` layers to show false-positive classes.
9. User isolates a track and watches its lane across the timeline.
10. User opens the Rerun recording for deeper temporal/MOT playback.
11. User opens the exact MLflow run and sees the same run id plus linked artifacts.
12. User switches to Forensic Review Bay if engineering wants all intermediate views.
13. User switches to Annotation Handoff when a reviewer needs to correct questionable decisions.

## Error And Degraded States

If a video is missing:
- Viewer panel shows `input video missing` with clip id, expected path, and artifact-generation action.

If overlay video is missing:
- Viewer falls back to raw video plus canvas overlay if event data exists.
- If event data is also missing, the panel shows the missing artifact boundary.

If timeline data is missing:
- The page still opens the run summary but disables playback review and tells the user to regenerate review artifacts.

If platform deep link is missing:
- Platform Bridge shows `not exported`, `degraded`, or `unsupported` with the stored error from platform export status.

If unsupported spec capability is selected:
- Inspector explains that the current run cannot prove that case and names the required data or implementation.

## Performance Budget

Targets for a 3-clip smoke run on local Docker:

- Story page first contentful UI: under 2 seconds after HTTP response starts.
- First playable selected clip: under 5 seconds when overlay videos exist.
- Playback overlay sync drift: less than 1 frame after startup.
- Timeline interaction: no visible lag for 100k frame events.
- React render cadence during playback: bounded; no per-frame whole-page render.

Implementation requirements:
- Precompute overlay videos and timeline JSON after run completion.
- Use browser video decode for video panes.
- Use canvas for interactive overlays and timeline.
- Virtualize event and table rows.
- Keep raw Parquet as backend artifact, not browser payload.
- Cache immutable clip review artifacts by URL and content hash.

## Acceptance Checks

Browser proof must validate:

- `docker compose up -d` starts the Workbench stack.
- A user can run smoke from the Workbench button.
- Run detail exposes `Open Story Review`.
- Story page loads through `http://10.7.0.4:60050`.
- The selected clip video is visible and playable.
- Raw and adapter views remain synchronized while scrubbing.
- Timeline markers update the selected frame.
- Selecting a rejection marker updates the inspector with stage, reason, decision, and track id when available.
- Track isolation visibly dims unrelated boxes.
- Edge-case taxonomy shows implemented, heuristic, and unsupported states.
- MLflow link opens the exact run, not the generic home page.
- Rerun/FiftyOne/Label Studio links carry the current run and clip context when exported.
- Browser screenshots prove the default layout, forensic layout, and annotation handoff layout.
- Browser diagnostics report frame budget, asset load time, and sync-drift scalar observations.

## Self-Review

- No incomplete markers remain in this design.
- The scope is focused on the story page blocker and Phase 1 visual-review journey.
- Phase 2 integrations are named only where they affect story-page affordances.
- The data model distinguishes authoritative run tables from review-optimized browser artifacts.
- The edge-case taxonomy separates implemented behavior from heuristic and unsupported cases.
- The layout strategy reuses FlexLayout and Biodock workspace patterns without copying incompatible domain code.
