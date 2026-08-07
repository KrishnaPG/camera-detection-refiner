# HandDetect Local DX

Start everything:

```bash
docker compose up -d
```

Open:

- Workbench: http://localhost:8000
- MLflow: http://localhost:5000

Use the Workbench button to run the smoke experiment, inspect reports, and replay a run with an override.

Default local runtime state is under `/tmp/handdetect`; run artifacts are under `runs/`.

No hardcoded username/password credentials are used in the default local setup.
