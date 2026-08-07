# HandDetect Local DX

Start everything:

```bash
docker compose up -d
```

Open:

- Workbench: http://localhost:8000
- MLflow: http://localhost:5000
- FiftyOne: http://localhost:5151
- Label Studio: http://localhost:8080

Use the Workbench button to run the smoke experiment, inspect reports, and replay a run with an override.

Default local runtime state, including run artifacts, is under `/tmp/handdetect`.
Generated state is pruned automatically; defaults keep 5 suites, cap runtime state at 20 GiB, and preserve 5 GiB free disk.

Local Label Studio credentials:

- Email: `handdetect@example.local`
- Password: `handdetect-local`
- API token: `handdetect-local-token`
