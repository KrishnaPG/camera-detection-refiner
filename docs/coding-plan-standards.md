> Mandatory for AI agents creating plan documents. No exceptions, shortcuts, placeholders, nor simplifications. Any MUST/NEVER violation is a defect.

NEVER create the plan as one large monolith document. MUST split the plan into smaller self-contained files, with an index for ready access. 

# Protocol

The index MUST add these below sections into its preamble. Missing section = invalid plan. Generic claims like “improve cohesion”, “optimize performance”, “use best practices”, “add validation”, or “use reusable code” are invalid unless they are tied to named modules, types, functions, packages, or flow stages. Use bullets, not tables.

## 1. Goal, Non-Goals, Delete List
- Final user-visible outcome:
- Non-goals:
- Planned items removed because they do not directly serve the final outcome:

## 2. End-to-End Flow Map
Map the flow before designing classes. For each stage, specify:
`input type/state -> owner module -> transform -> output type/state -> validation/revalidation -> persistence/external call -> async/concurrency -> copy/serde -> error path`.

The map MUST include all inputs, outputs, transforms, validation points, ownership changes, persistence points, external calls, async/concurrency boundaries, memory-copy points, serde points, and error paths.

## 3. Structure Derived From Flow
First, Go through the requirements to identify all reusable patterns that can be created as standalone modules/packages that can be reused across various projects, and document them; once done, do another round to identify second level of reusable patterns that can be composed from the first-level ones and document them. Repeat this process till no further patterns can be found. The list of all reusable packages identified in all rounds together with the remaining domain/business specific feature/modules become the final list of modules; Document that list.

Then, derive the code structure only in this order: features/modules -> public interfaces -> classes/structs -> functions -> code. Do NOT design classes before module/flow ownership is known.

For each module, specify:
- contiguous flow stage owned by the module
- upstream caller and downstream consumer
- input/output domain types or native library result shapes
- what the module must never own
- reusable patterns identified

## 4. Validation, Resource Lifetime, Boundary Transfer, and Test Plan
- Validation path: `Raw*`/`Untrusted*` -> one parser/validator -> `Validated*`/domain type -> internal processing without full revalidation.
- Revalidation triggers only: network/IPC, serde, persistence read, cache read, user input, or transform that creates new invariants.
- Boundary transfer: cross-module transfer MUST be a typed domain object or native library result shape. Custom DTOs/wrappers/envelopes are allowed only at real external protocol boundaries.
- State-machine path: stateful flow -> typed states/events -> exhaustive transitions/guards -> transition side effects -> terminal/error/cancel states -> persistence/recovery.
- RAII path: required resource -> ready handle type -> factory/context manager -> failure before object creation -> cleanup owner.
- Test path: staged infra -> seed/setup script -> seed manifest ids/keys -> production entrypoints -> cleanup by run id/namespace.

Forbidden: validation flags, duplicate full validation in one flow, two-phase resource init, fake test data, fake providers, fake app behavior, and internal serde just to cross modules.

## 5. Reuse and Performance Plan
For each reusable pattern, specify the package/helper/registry selected. If custom code is used, name the battle-tested package considered and rejected, and explain why.

For each hot path, specify copy/serde removed, zero-copy path preserved, batching/parallelism/cache opportunity, bounded concurrency/backpressure rule, and any advanced technique used or rejected. Do not mention SIMD, SSE, AVX-512, workers, streaming, caching, or batching unless tied to a named hot stage.

## 6. Second-Pass Audit
After the first plan, you MUST do one more audit pass and list concrete changes made for deleted low-value features, removed duplicate concepts, reused package/helper, reduced copy/serde, validation state, boundary transfer, RAII/resource ownership, test realism, and frontend re-render avoidance if UI code changed. If this changes flow ownership, validation state, or module boundaries, repeat sections 2-6 once again.

The implemented code must strictly adhere to [Coding Standards](./coding-standards.md).