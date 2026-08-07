# HandDetect Quality Workbench

`docker compose up -d` starts the full local workbench stack on the host IP and ports from `.env`:

- Workbench: `http://10.7.0.4:60050`
- MLflow: `http://10.7.0.4:60900`
- Evidently: `http://10.7.0.4:60904`
- FiftyOne: `http://10.7.0.4:60901`
- Label Studio: `http://10.7.0.4:60902`

Use the Workbench UI to trigger a smoke run, inspect artifacts, and replay prior runs.

Local Label Studio credentials:

- Email: `handdetect@example.local`
- Password: `handdetect-local`
- API token: `handdetect-local-token`

Developer-only host commands are available after `make bootstrap`:

```bash
make seed
make run CONFIG=configs/smoke-experiment.toml
python -m handdetect.cli.main review open --suite-id <suite_id> --run-id <run_id>
```

Default local runtime state, including run artifacts and third-party tracking files, is under `/tmp/handdetect`.
Docker service backing stores are under `/tmp/handdetect-services`.
Generated state is pruned automatically; defaults keep 5 suites, cap runtime state at 20 GiB, and preserve 5 GiB free disk.
Runtime retention runs automatically with `HANDDETECT_KEEP_SUITES`, `HANDDETECT_MAX_RUNTIME_BYTES`, and `HANDDETECT_MIN_FREE_BYTES`.
The `dvc` status surfaced in run artifacts is DVCLive metrics output only; replay restore authority in this assignment remains content-hash snapshot lineage, even when a replay worktree can execute `dvc pull`/`checkout`.
CVAT and Datumaro are surfaced as run-scoped handoff manifests; set `HANDDETECT_CVAT_PUBLIC_URL` when a CVAT service is available.
