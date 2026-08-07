> Mandatory for React/webui code. Any MUST/NEVER violation is a defect.

# State Ownership
- TanStack Query `useQuery`/`useMutation` owns request/response remote data: REST calls, JSON-RPC method calls, immutable snapshot fetches, cacheable reads, retries, invalidation, mutation status, optimistic updates, and stale-time semantics.
- TanStack Query MUST NOT be used as the default owner or event bus for long-lived push channels such as WebSocket, WebTransport, WebRTC DataChannel, SSE, worker streams, native streams, or transport sessions that deliver many frames after one negotiation.
- Long-lived push-channel data MUST be owned by a stream/session adapter with explicit lifecycle, cancellation, bounded buffering, backpressure, decoding, error handling, and cleanup. React hooks/components MUST NOT own transport read loops directly.
- Multiplexed push channels MUST route frames by typed stream/view/panel identifiers through a registry or stream session service. A single transport may feed multiple panels/views, but each consumer MUST subscribe through a typed selector or subscription handle instead of reading the raw channel.
- Valtio owns local UI state and UI-facing stream reactivity: selected nodes, active panels, timestep, brush windows, layout preferences, transient viewer state, selected stream subscriptions, coarse stream status, unread counts, cursor/watermark summaries, and derived calculations based on server data or stream state.
- Valtio may hold non-serializable stream/session handles through `ref()` when UI actions need access to a long-lived channel, reader, decoder, `AbortController`, or session lease. Those refs MUST be treated as non-render-driving resources and cleaned up by the owning stream/session adapter.
- Valtio MUST NOT proxy high-frequency raw packet buffers, unbounded row streams, or transport frame queues directly into React render flow. Hot buffers stay inside stream/session adapters or behind `ref()` handles with bounded capacity and coarse reactive version counters.
- JSON-RPC events and data-channel frames MUST decode into typed UI intents through a registry. Components MUST NOT switch on raw backend payloads inline.
- Prefer mature open-source packages and existing `frontend/packages/*` owners over custom UI/dataflow plumbing. New package names are capability labels until an audit proves no existing owner fits.

# Valtio Access Rules
1. Before every Valtio read, classify the read as render-driving or non-render-driving.
2. Render-driving read = value directly changes JSX, props, className, visible text, enabled/disabled state, or rendered component choice. Use `useSnapshot(store.slice)` and subscribe only to the smallest slice/key needed for that render.
3. Non-render-driving read = value is used inside event handlers, callbacks, services, commands, timers, promises, subscriptions, stream/session adapters, viewer adapters, workers, animation loops, or pure functions needing latest state. Read directly from the raw proxy: `store.slice`. Do not use `useSnapshot` for these reads.
4. `useSnapshot(store)` on a broad/root store is forbidden. Snapshot only the smallest store slice used by the JSX in the same component.
5. Do not create a snapshot only to pass data into callbacks, services, adapters, or actions. Those must read latest state from the raw proxy directly at execution time.
6. High-frequency state such as 3D camera, pointer position, timestep, brush movement, playback frame, stream packets, stream decoder buffers, transport progress, hover state, and viewer internals MUST stay out of React render flow. Use raw proxy reads, `ref()` handles, subscriptions, stream/session adapters, or viewer adapters. Expose only coarse/throttled render state to React.
7. `ref()` may store non-serializable handles and hot mutable structures only when they are non-render-driving: transport sessions, readers, decoders, abort controllers, bounded ring buffers, viewer instances, and worker handles. Render-driving state must be mirrored only as coarse typed fields such as `status`, `version`, `cursor`, `watermark`, `unreadCount`, or `lastError`.
8. Multiplexed stream state in Valtio MUST be keyed by typed logical identities such as panel id, view id, stream id, materialization id, or subscription id. Components subscribe to the smallest logical key they render.
9. Client-state mutations MUST occur through named store actions only. Components must not assign proxy fields inline.

# Store And Adapter Shapes
- Valtio store modules MUST export typed state, a single proxy instance, and named action functions. App-level stores live under `frontend/app/src/state/`; reusable stores live in the owning `frontend/packages/*` package.
- Valtio actions MUST be the only place that mutates proxy fields. Components, panels, adapters, and tests call actions or package APIs; they do not write `store.x = value` inline.
- Store state MUST use typed scalar fields, branded ids, readonly arrays for bounded metadata, and package-owned handles through `ref()`. It MUST NOT hold raw packet buffers, Arrow batches, artifact bytes, SQL rows, tokens, presigned URLs, or backend response objects.
- Stream/session adapters MUST expose start/stop/subscribe or acquire/release APIs that are valid-if-created and clean up exactly the resources they acquire.
- Adapters, sessions, lifecycle hooks, and reusable package hooks MUST NOT use React hook state as their data owner. `useEffect` is allowed only for acquire/start/subscribe/cleanup glue, `useMemo` must not be used as a cache or lifecycle guard, and render-driving state must be stored in Valtio, TanStack Query snapshots, or reusable stream/session registries. Existing adapter hook debt MUST only shrink under the drift gate.

# Long-Lived Push Channels
- Stream/session adapters own WebSocket, WebTransport, WebRTC DataChannel, SSE, worker, and native transport lifecycles. They MUST expose start/stop/subscribe APIs that are valid-if-created and clean up the same resources they acquire.
- Stream/session adapters MUST validate external frames exactly once at the transport boundary, decode to typed domain/UI intents, and route by typed channel identity. Components and Valtio actions receive validated intents, not raw frames.
- Stream/session adapters MUST apply bounded buffering, backpressure, cancellation, timeout, retry, reconnect, and close semantics explicitly. Unbounded queues, unbounded `while` loops in React hooks, and per-frame React state setters are forbidden.
- Multiplexed streams MUST separate transport identity from consumer identity. Transport sessions own physical connections; panel/view subscriptions own logical interest, cursor, watermark, schema version, and cleanup.
- Snapshot-then-tail flows MUST use TanStack Query only for immutable/cacheable snapshot requests when appropriate. The live tail MUST be owned by a stream/session adapter. Snapshot/live reconciliation, cursor-too-old, schema-change, governance-change, and resnapshot behavior MUST be explicit.
- Stream adapters may publish coarse render-driving state through Valtio: status, version counters, latest cursor, latest watermark, unread count, selected materialization, or last error. They MUST keep raw packet buffers, decoder state, and transport handles outside render-driving state.

# Generated Contracts And DTO Boundary
- Frontend modules MUST use generated Berg10/OpenRPC TypeScript contracts for backend data shapes. If a backend field is wrong or missing, fix the Rust/OpenRPC schema and rerun generation; do not hand-patch generated outputs.
- App code MUST NOT define hand-authored DTO mirrors for Berg10 RPCs, diagnostics, C-view rows, rawStream frames, package descriptors, auth claims, or generator commands.
- `unknown`, `any`, `Record<string, unknown>`, and broad dictionaries are allowed only inside explicit boundary decoders, generated-code compatibility shims, or package validators. They MUST NOT enter Valtio state, React props, or app panel internals as durable shapes.
- Boundary decoders validate once, produce typed domain/UI intents, and then disappear from hot render paths. Components and Valtio actions receive typed values only.
- Diagnostics/activity state MUST contain metadata only: typed ids, states, phases, counters, timestamps, trace/span ids, and redacted errors. It MUST NOT contain payload bytes, SQL text, rows, artifact bodies, presigned URLs, tokens, or raw logs.

# FlexLayout Boundary
- FlexLayout remains the only owner of dock topology: model tree, tabsets, selected tabs, visible tabs, tab order, split geometry, floating windows, and serialized layout JSON.
- Valtio may store active layout/theme preference, dock command status, coarse dock version, and user-visible command errors. It MUST NOT store visible-panel mirrors such as `visiblePanelsByWorkspace`, `visiblePackageTabs`, or derived tab maps.
- Query visible tabs with FlexLayout `Model`/`ILayoutApi` on demand from a dock query adapter. Do not calculate visibility in React components.
- FlexLayout model mutations go through FlexLayout actions or registered dock commands. Components dispatch named commands such as `openOrFocusPanel`; they do not mutate tab topology directly.
- Layout/theme persistence must use the workspace persistence boundary and survive browser refresh without duplicating layout state in app stores.

# Modularity And JSX
- Files MUST stay below 450 LOC. React components and functions MUST stay below 50 LOC. Split into feature modules, hooks, actions, registries, sub-components, and pure helpers.
- Components MUST NOT calculate/transform data. Use custom hooks, pure helpers, TanStack Query `select`, Valtio selectors, or named store actions.
- Components MUST NOT contain `useEffect`. Effects, subscriptions, layout persistence, and third-party viewer integration MUST live in custom hooks/adapters.
- Render components MUST NOT import or call `useState`, `useEffect`, `useMemo`, or `useReducer`. Local render-driving state belongs in Valtio stores/actions; derived render values belong in selectors, pure helpers, TanStack Query `select`, or reusable package hooks.
- Custom hooks and adapters that use React lifecycle hooks MUST be named and located as lifecycle owners, such as `*.adapter.ts`, `*.session.ts`, `*Lifecycle.ts`, `use*Lifecycle.ts`, or reusable package hooks. They must own acquire/start/subscribe/cleanup boundaries explicitly and must not be disguised as render components.
- Existing render-component hook debt MUST only shrink. New files or touched files must not add `useState`, `useEffect`, `useMemo`, `useReducer`, broad `useSnapshot(store)`, or inline Valtio proxy mutation in `.tsx` render components; update the drift gate only when removing debt or when documenting a true adapter exception.
- JSX event handlers such as `onClick`/`onChange` MUST be named functions declared before `return` or imported action callbacks.
- Dynamic rendering MUST use lazy component registry dictionaries. Do not hardcode large conditional render blocks.
- Use branch-less, state-based UI fragments; JSX MUST avoid `if/else` branching. Use early returns, registry lookup, polymorphic components, or small state-specific components.
- MUST use dynamic imports for route/panel/event-based components.

# Styling And Visuals
- Use CSS Modules with reusable class names. No inline styles except isolated third-party visualization adapters.
- Use `rem`, not `px`, for font sizing. Body text is `1rem`/16px. Heading scale uses a 1.333 ratio.
- Do not pass new object/array/function literals to heavy children, viewers, grids, charts, or 3D adapters on every render. Move them outside React render flow.
- Third-party viewer/chart/3D instances MUST be owned by adapter hooks/components with explicit create/update/dispose lifecycle. Do not let normal React components manage imperative viewer internals directly.
- Custom hooks that perform subscriptions, timers, sockets, observers, workers, or viewer integration MUST clean up deterministically and handle cancellation/race conditions.

# Performance And Memory
- Render paths MUST NOT materialize rows, clone artifact bytes, clone Arrow batches, or copy stream payload buffers. Hot data stays in columnar stores, decoder caches, viewer refs, stream adapters, or package-owned bounded rings.
- Large immutable data moves by reference through typed handles or `Bytes`/Arrow/native objects at the boundary. UI state receives only scalar status, ids, cursors, watermarks, unread counts, versions, and redacted error handles.
- Animation-frame, pointer-move, drag, hover, playback, and streaming updates MUST NOT call React state setters per frame. Keep hot state in raw proxy/ref/viewer layer and publish coarse UI state only when needed.
- Bounded rings, feed stores, resource leases, and keyed stream state MUST come from reusable packages such as `shared-feed-registry`, `lifecycle-leases`, `current-state-feed`, or `valtio-stream-state`. Do not hand-roll duplicate maps, ref counters, or unbounded queues in app modules.
- Query keys MUST be typed/factory-created. Do not use ad-hoc array literals spread across components. Query invalidation MUST be targeted; do not invalidate broad query groups unless the mutation truly changes every query in that group.

# Exception Policy
- Exceptions MUST name the owning file, owning module, reason, lifecycle cleanup, and enforcing drift test. A comment such as "temporary" is not an exception.
- Exceptions MUST be local to the real owner: viewer lifecycle in a viewer adapter, stream lifecycle in a stream/session adapter, query state in a query hook, and UI chrome state in a Valtio store.
- Exceptions MUST NOT add product-specific DTOs, raw backend payload switching, unbounded queues, broad Valtio snapshots, or component-local render state.
- Any baseline exception in a drift test may only shrink unless the user explicitly approves a documented architectural exception.

# Testing And Product Proof
- Frontend tests MUST use the real app data path. Do not mock TanStack Query results, REST clients, JSON-RPC events, Valtio stores, FlexLayout state, nor viewer adapters. Tests MUST run against staged backend endpoints seeded by the backend seed scripts. Components may be tested only with real providers configured for the staged environment.
- Unit tests are allowed for reusable package APIs and drift gates. They are not a replacement for browser-visible staged product proof.
- Product acceptance must exercise the visible UI, generated clients, real stream/session adapters, Valtio stores, FlexLayout model, and browser-visible diagnostics.

# Enforcement Index
- `frontend/app/test/reactComponentStateDrift.test.ts`: shrinking baseline for render-component hooks, adapter hook debt, broad `useSnapshot(uiStore)`, inline Valtio mutation, and required standards wording.
- `frontend/app/test/p2fsCopilotPanelArchitecture.test.ts`: P2FS panel architecture drift checks for local state, visible-tab mirrors, and generator command loop guards.
- `frontend/app/test/workspaceFeedOrchestrator.test.ts`: workspace feed reconciliation and shared-feed lifecycle expectations.
- `frontend/app/test/workspaceUserPreferences.test.ts`: layout/theme persistence behavior.
- `frontend/packages/shared-feed-registry/test`: reusable shared feed/session lifecycle behavior.
- `frontend/packages/valtio-stream-state/test`: coarse keyed stream state and bounded projection behavior.
- `frontend/packages/berg10-client/test/diagnosticsArchitecture.test.ts`: generated diagnostics client and contract boundary checks.
