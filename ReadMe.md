# HandDetect Local DX

Start everything:

```bash
docker compose up -d
```

Open:

- Workbench: http://localhost:8000
- MLflow: http://localhost:5000

Use the Workbench button to run the smoke experiment, inspect reports, and replay a run with an override.

Default local runtime state, including run artifacts, is under `/tmp/handdetect`.
Generated state is pruned automatically; defaults keep 5 suites, cap runtime state at 20 GiB, and preserve 5 GiB free disk.

No hardcoded username/password credentials are used in the default local setup.
