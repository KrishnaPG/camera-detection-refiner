# HandDetect Quality Workbench

`docker compose up -d` starts the local workbench at `http://localhost:8000` and MLflow at `http://localhost:5000`.

Use the workbench UI to trigger a smoke run, inspect artifacts, and replay prior runs. CLI equivalents:

```bash
make seed
make run CONFIG=configs/smoke-experiment.toml
python -m handdetect.cli.main review open --suite-id <suite_id> --run-id <run_id>
```

No hardcoded application credentials are required in the default local setup.

Default local runtime state, including run artifacts and third-party tracking files, is under `/tmp/handdetect`.
Runtime retention runs automatically with `HANDDETECT_KEEP_SUITES`, `HANDDETECT_MAX_RUNTIME_BYTES`, and `HANDDETECT_MIN_FREE_BYTES`.
The `dvc` status surfaced in run artifacts is DVCLive metrics output only; replay restore authority in this assignment remains content-hash snapshot lineage, even when a replay worktree can execute `dvc pull`/`checkout`.
