> Mandatory for AI agents. No exceptions, shortcuts, placeholders, nor simplifications. Any MUST/NEVER violation is a defect.

You MUST produce for high-performance, future extensible, loosely coupled modules with branch-less programming and zero-memory copy.

# Dependencies

- MUST prefer mature libraries over custom code: e.g. `tenacity` for retries, `structlog` for logging, `pydantic` for validation. Do not reinvent stable libraries.
- Pin exact latest stable versions from PyPI/npm at implementation time. Never use unbounded `>=X.Y` in production.
- Add a dependency only when stdlib/current deps cannot solve the problem cleanly.

# Code Organization

- Imports MUST be at module top. Never import inside functions; fix cycles by restructuring modules.
- Files MUST stay below 450 LOC. Functions MUST stay below 50 LOC. Split before exceeding.
- Duplicated logic is forbidden. At the second occurrence, extract a helper, registry, strategy, or shared utility.
- Logic MUST NOT contain raw literals that affect behavior, identity, I/O, protocol, storage, validation, performance, limits, env/config, observability, UI state, or domain meaning. This includes paths, URLs, routes, buckets, tables/columns, queues/topics, env keys, metric/log keys, statuses, ports, timeouts, retries, batch sizes, limits, flags, and domain constants. Use typed constants/enums/config and centralized builders only.
- Only path/URL/resource builders may assemble paths, URLs, routes, object keys, endpoints, or storage ids. Callers pass typed parts, never concatenated strings. Allowed raw literals in logic: `None`, empty collections, local loop indexes, `0`/`1` counters, comparison booleans, and error/log message text.
- Constants, magic values, and enums MUST live in dedicated files, e.g. `constants.py`, `enums.py`. No scattered literals.
- One module = one concept. Example: `mafft.py` contains only MAFFT logic.

# Type Safety

- Every function parameter and return value MUST be annotated.
- `Any` is forbidden except at untyped third-party boundaries; comment the library and reason.
- Domain fields MUST use specific types/enums/newtypes, not raw `str`/`int`/`float`/`bool`. It must be impossible to assign A id to B id, path to hash, level to family, etc.
- NEVER erase domain types at internal boundaries. No `dict[str, Any]`, raw JSON, free strings, or generic payload maps after validation.
- Do not hide domain branching inside string comparisons. Use typed enums, registries, strategy maps, or typed dispatch tables.
- Domain/API models MUST use Pydantic v2 `BaseModel`. No dataclasses, attrs, or TypedDict for API contracts.
- Code MUST pass `mypy --strict` with zero errors.

# Comments and Ownership Docs

- Every non-obvious design choice MUST have a nearby comment in the code: choice, reason, assumptions, consequences, and future-drift guard.
- Each module/feature header MUST state: purpose, ownership boundary, how/when to use, upstream/downstream users, when not to use, limitations, future planned enhancements and linked design choice.
- Do not comment obvious code. Comment invariants, boundaries, identity rules, lifecycle rules, and constraints that agents are likely to break.
- New code MUST align with existing comments. If code intentionally changes an earlier design choice, update the comment first. Code must never contradict comments.

# Validation, Errors, and Observability

- Fresh external data enters as `Raw*`/`Untrusted*` only. Exactly one boundary parser validates it and returns a `Validated*`/domain type.
- Internal modules MUST accept validated/domain types and MUST NOT re-run full validation in the same flow.
- Re-validate only after network/IPC, serde, persistence read, cache read, user input, or a transform that creates new invariants.
- Validation state MUST be represented by types, never by flags. Do not use `validate: bool`, `skip_validation`, `already_validated`, or `trusted=True`.
- Pydantic `model_validate` MUST appear only in boundary parsers/adapters. Internal code passes validated model instances directly. Do not convert validated objects back to `dict`/JSON for internal transfer.
- Fail fast and early. Never silently coerce, default, or ignore invalid data.
- Bare `except:` is forbidden. Catch specific exceptions; `except Exception as e` is the minimum fallback.
- Every error MUST include OTel context: `job_id`, `step_id`, `phase`, traceback, and relevant domain ids.
- Every caught exception MUST be logged and metrics-incremented, or re-raised.

# Memory, Performance, and Resource Lifetime

- Aim for zero-memory copy. Use memoryviews, buffer pools, generators, native result shapes, and streaming over list materialization.
- Never load multi-GB files into memory. Stream with generators/iterators.
- No avoidable short-lived allocations in loops. Pre-allocate buffers, reuse objects, and use `__slots__` where appropriate.
- Reuse HTTP, DB, and OTLP connection pools. Never create per-request connections.
- Avoid per-row/per-item serde across internal boundaries. Preserve typed/native shapes until external serialization.
- Resource-owning objects MUST be valid-if-created. No two-phase initialization. Required resources MUST be acquired, checked, and wrapped as typed ready handles before object construction. If any required resource is unavailable, the factory/context manager MUST fail and return no object.
- Required resource fields MUST be non-optional. Do not use `Optional[Db]`, `Optional[Client]`, `Optional[Path]`, or nullable handles for resources required by the object. Constructors accept ready handles only.
- Resource cleanup MUST be owned by the same factory/context manager that acquired the resource. Use `with`, `async with`, `ExitStack`, or `AsyncExitStack`. Do not rely on `__del__`.
- Long-lived push channels are not request/response caches. WebSocket, WebTransport, WebRTC DataChannel, SSE, worker streams, and native streams MUST be owned by stream/session adapters with explicit lifecycle, cancellation, bounded buffering, backpressure, decoding, fanout, and cleanup. Multiplexed streams MUST route frames by typed logical identities.

# Patterns

- MUST strictly use state-machine based logic as much as possible. Any lifecycle, async workflow, protocol/session, resource status, retry/cancel/pause/resume flow, or mutually exclusive mode MUST define typed `State` and `Event` values and one exhaustive transition table/handler. State changes MUST occur only through named events; invalid transitions MUST fail; transition handlers own guards, side effects, persistence, metrics, and cleanup. NEVER encode state as scattered booleans/nullables or ad-hoc branch chains. Instead maintain a registry of functions for each state and switch them based on the current state;
- Domain dispatch MUST use registries, strategies, function pointers, or factories instead of hardcoded `if/elif/else` or `switch` chains. Guard clauses for validation, resource checks, and error paths are allowed.
- REST endpoints are transport wrappers only. Zero domain logic in API handlers.
- Pass dependencies explicitly. No global singletons except configuration.
- Register tools, gates, backends, and transports through central registries with decorator discovery.
- Use factories for transport/backend construction.
- Waiting MUST be signal-driven, never polling-driven. Threads/tasks MUST NOT wait using `sleep` loops, timed polling, repeated readiness/status checks, or spin-waits. Use condition variables, events, semaphores, futures, channels/queues, async notifications, OS wait handles, `select`/`poll`/`epoll`/`kqueue`, or I/O completion ports. Re-check the wait predicate after wake-up. Timeouts may bound an event wait; `sleep` is allowed only for explicit rate limiting or bounded retry backoff, never to detect readiness or completion.
- Observability (metrics, traces, logging) MUST be first-class citizens in the code with zero overhead:
  - Use static metric names/constants.
  - Emit only phase-level metrics, not row/batch-level events.
  - No allocation-heavy formatted strings on hot paths.
  - No SQL result rows, Arrow bytes, Parquet bytes, or presigned URLs in logs/spans.
  - Use existing tracing level filtering so disabled spans are near-zero overhead.
  - Metrics MUST be scalar counters/histograms only.
  - Export failures MUST NEVER block the product functionality.

# Code Quality

- No `pass`, `TODO`, `raise NotImplementedError`, placeholder functions, or future stubs. Implement or remove.
- Code MUST handle empty inputs, missing files, network timeouts, invalid configs, partial failures, and invalid external responses.
- Every path MUST preserve validation state, invariants, error handling, logging, and metrics where applicable; do not duplicate full validation on validated/domain types.
- Async code MUST NOT perform blocking file, network, CPU, compression, embedding, image/video, or model work on the event loop. Use async libraries, worker threads/processes, or external job systems.
- For Berg10-owned internal work items, "external job systems" means Rust-owned worker processes for all known checked-in work. Other language workers may exist only in user-space/user-container extension boundaries or as subprocess domain adapters invoked by a Rust worker; they must not own Berg10 internal leases, queues, command terminal states, or trace roots.
- Concurrency MUST be bounded. No unbounded `gather`, task spawning, queue growth, retries, or fanout. Use explicit limits, backpressure, cancellation, and timeouts.
- Retry only idempotent operations or operations with an idempotency key. Retries MUST have bounded attempts, jitter/backoff, timeout, and structured logging.
- Cache ownership MUST be explicit: owner, key type, invalidation trigger, TTL/lifetime, mutability rule, and whether cached values may be shared or copied.
- Core logic MUST NOT call time, random, UUID, environment, filesystem, or network directly. Inject providers/handles so tests and replay are deterministic.

# Test Realism Rules

- Tests MUST always execute code against live, real staged infrastructure. No mocks, stubs, fake repositories, fake databases, in-memory substitutes, monkeypatch-returned outputs, demo code, hardcoded sample records, local JSON fixtures pretending to be stores, nor test-only branches. NEVER use fixture/offline tests.
- Tests MUST enter only through user-facing surfaces: public client APIs, REST/JSON-RPC/Flight/Lakehouse protocols, CLIs, or UI flows. Tests MUST NEVER import internal modules, call internal methods, invoke worker internals directly, or assert behavior through code paths that a real client/operator cannot use. All Tests MUST comply - no exception.
- Each feature MUST have only unique, user-meaningful acceptance tests. Prefer 1-2 end-to-end tests per feature unless distinct user workflows require more; do not create broad stale test suites that only restate implementation structure.
- Feature coverage means a real client/operator workflow succeeds end-to-end through the public surface. Source scans, config/file/route/schema/dependency existence checks, wiring assertions, and implementation-shape tests are NOT feature coverage.
- Drift guards that inspect source or configuration may exist only as supplemental safety checks. They MUST be named as drift guards, MUST NOT be counted as feature proof, and MUST NOT replace acceptance tests.
- Acceptance tests MUST assert real user-observable behavior: client-visible rows, bytes, files, UI state, live frames/events, CDC/materialization outputs, protocol responses, or capability-specific errors from the public surface.
- Missing functionality MUST fail through the same real client call a user would make, with a capability-specific error message naming the missing public surface or client operation. Tests MUST NOT silently skip, pass from metadata, or pass from source/config assertions when the capability is absent.
- If a feature depends on third-party clients or servers such as ClickHouse, Dremio, object stores, queues, or browsers, the acceptance test MUST start them through Docker Compose or an equivalent staged environment and stop them after the test unless an explicit debug keep flag is set.
- Test config may change only env names, credentials, endpoints, database/schema names, bucket prefixes, and run ids. It MUST NOT swap provider classes, storage engines, query engines, validation paths, serializers, repositories, clients, or business logic.
- Staged data MUST be created before tests by versioned deterministic seed/setup scripts against the real staged databases, object stores, catalogs, queues, indexes, and services.
- Test cases MUST NOT prepare data inline. They may only reference seeded scenario ids/keys from the seed manifest, call production entrypoints, assert results, and clean up by run id/namespace.
- Data created during a test is allowed only when creation/mutation is the production behavior under test; its input must come from the seed manifest.
- CI MUST fail on mocking/faking tools or fake app behavior in tests: `mock`, `patch`, `MagicMock`, fake repos/clients/DBs, MSW-style fake APIs, hardcoded fixture payloads, or local files pretending to be remote stores.
- Product MUST be tested at each stage of development regularly as if you are a user, end-to-end. Not just running test-cases;

See [Frontend UI Coding Standards](./coding-standards-frontend.md) for frontend/UI rules.

See [Berg10 Rules](./coding-standards-berg10.md) for Berg10-specific rules.

See [Repo Dx Rules](./coding-repo-standards.md) for repository setup, DX, Docker and build configuration rules.
