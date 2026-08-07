# Final Review Fixes Report

Date: Friday, August 7, 2026
Branch: `bytetrack-quality-workbench-implementation`

## Scope

Addressed all Critical and Important findings from `/tmp/handdetect-final-review-findings.txt`:

- replay restore/runtime-root correctness
- FiftyOne decisions lookup robustness when `frame` is absent
- Evidently export package-API usage with degraded fallback semantics
- Label Studio idempotent publish behavior
- audit decision reject-reason preservation for temporal and over-cap cases

## Red -> Green Evidence

### 1. Replay restores inputs from the isolated worktree and writes child artifacts to main run roots

Red:

- replay previously coupled restored inputs and output roots incorrectly
- non-DVC restores could imply DVC work happened when no DVC metadata existed
- worktree restore behavior was not covered tightly enough

Green:

- replay now detects DVC metadata inside the restore worktree and runs restore steps there
- when DVC metadata is absent, replay explicitly restores from lineage source snapshot/content refs and records that mode instead of claiming DVC work
- child config now points input roots at restored worktree data while output artifacts intentionally land in the main runs root
- acceptance coverage added for both non-DVC restore behavior and DVC restore invocation

### 2. FiftyOne sample publication no longer collapses to hidden `path_only` on schema mismatch

Red:

- publication path could fail when decisions parquet lacked `frame`, causing real sample publishing to degrade behind fallback behavior

Green:

- decisions lookup now supports `frame`, `frame_index`, and detection-id-based filtering
- acceptance coverage exercises a real sample publication path without `frame` so schema drift is caught before fallback hides it

### 3. Evidently export uses the package API when available and degrades honestly on failure

Red:

- export path could report `exported` while writing a handwritten substitute instead of a real Evidently report

Green:

- export now attempts the installed Evidently API first
- if API import or rendering fails, the tracker returns degraded status and a fallback artifact instead of claiming success
- acceptance coverage verifies both the package path and degraded fallback path

### 4. Label Studio publish is idempotent

Red:

- reruns could create duplicate projects/tasks even when an import manifest already existed

Green:

- existing import manifest is now treated as the source of truth for project/task reuse
- acceptance coverage verifies manifest reuse without creating duplicate remote state

### 5. Audit decisions preserve temporal and over-cap reject reasons

Red:

- temporal reject provenance and explicit max-two/over-cap reasoning could be lost in emitted decisions

Green:

- ledger building now carries temporal context through rejected detections
- over-cap rejections are preserved explicitly as `OVER_MAX_HANDS`
- acceptance coverage verifies provenance on emitted decision rows

## Files Changed

- `Dockerfile`
- `apps/handdetect-cli/src/handdetect/audit/ledger.py`
- `apps/handdetect-cli/src/handdetect/cli/main.py`
- `apps/handdetect-cli/src/handdetect/lineage/capture.py`
- `apps/handdetect-cli/src/handdetect/lineage/replay.py`
- `apps/handdetect-cli/src/handdetect/pipeline/clip_runner.py`
- `apps/handdetect-cli/src/handdetect/review/fiftyone_dataset.py`
- `apps/handdetect-cli/src/handdetect/review/labelstudio_client.py`
- `apps/handdetect-cli/src/handdetect/runtime_paths.py`
- `apps/handdetect-cli/src/handdetect/tracking_platforms/evidently_report.py`
- `apps/handdetect-cli/src/handdetect/workbench/server.py`
- `tests/acceptance/test_adapter_smoke.py`
- `tests/acceptance/test_lineage_replay.py`
- `tests/acceptance/test_tracking_review.py`
- `tests/acceptance/test_workbench_routes.py`

## Verification

Commands run:

```bash
python -m ruff format packages apps tests
python -m ruff check packages apps tests
python -m pytest tests/acceptance -q --basetemp=/home/ubuntu/workspace/hand-detect/.tmp/pytest
```

Results:

- `python -m ruff format packages apps tests` -> passed (`80 files left unchanged`)
- `python -m ruff check packages apps tests` -> passed (`All checks passed!`)
- `python -m pytest tests/acceptance -q --basetemp=/home/ubuntu/workspace/hand-detect/.tmp/pytest` -> passed (`31 passed, 1 warning in 72.27s`)

## Concerns

- Full acceptance validation needed a workspace-backed temp layout: `/tmp/handdetect` was redirected to `/home/ubuntu/workspace/hand-detect/.tmp/handdetect` and pytest used `--basetemp=/home/ubuntu/workspace/hand-detect/.tmp/pytest` to avoid tmpfs/quota churn during repeated review runs. The code is green under that stable layout, but the environment still has a history of tmp-root pressure.
