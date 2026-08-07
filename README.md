# HandDetect Quality Workbench

`docker compose up -d` starts the full local workbench stack:

- Workbench: `http://localhost:8000`
- MLflow: `http://localhost:5000`
- FiftyOne: `http://localhost:5151`
- Label Studio: `http://localhost:8080`

Use the Workbench UI to trigger a smoke run, inspect artifacts, and replay prior runs.

Developer-only host commands are available after `make bootstrap`:

```bash
make seed
make run CONFIG=configs/smoke-experiment.toml
python -m handdetect.cli.main review open --suite-id <suite_id> --run-id <run_id>
```

Local Label Studio credentials are documented in `ReadMe.md`.

Default local runtime state, including run artifacts and third-party tracking files, is under `/tmp/handdetect`.
Runtime retention runs automatically with `HANDDETECT_KEEP_SUITES`, `HANDDETECT_MAX_RUNTIME_BYTES`, and `HANDDETECT_MIN_FREE_BYTES`.
The `dvc` status surfaced in run artifacts is DVCLive metrics output only; replay restore authority in this assignment remains content-hash snapshot lineage, even when a replay worktree can execute `dvc pull`/`checkout`.
