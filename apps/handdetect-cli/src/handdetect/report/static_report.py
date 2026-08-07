from __future__ import annotations

import json
from html import escape
from pathlib import Path


class StaticReportBuilder:
    def build(self, run_root: Path) -> Path:
        manifest = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
        regression = json.loads((run_root / "regression.json").read_text(encoding="utf-8"))

        tracking = {}
        tracking_path = run_root / "tracking_export_status.json"
        if tracking_path.exists():
            tracking = json.loads(tracking_path.read_text(encoding="utf-8"))

        platforms_path = run_root / "review" / "platforms.json"
        platform_hint = "available" if platforms_path.exists() else "not yet generated"
        platforms = self._load_platforms(platforms_path)
        platform_links = self._platform_links(platforms)
        run_page_url = f"http://localhost:8000/runs/{manifest['run_suite_id']}/{manifest['run_id']}"
        run_page_path = f"/runs/{manifest['run_suite_id']}/{manifest['run_id']}"

        html = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <title>ByteTrack Detection Quality Workbench</title>
    <style>
      body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #18202a; }}
      main {{ max-width: 72rem; }}
      section {{ border-top: 0.0625rem solid #d8dee8; padding-top: 1rem; margin-top: 1rem; }}
      code {{ background: #eef2f7; padding: 0.125rem 0.25rem; border-radius: 0.25rem; }}
      pre {{
        white-space: pre-wrap;
        background: #f6f8fb;
        padding: 0.75rem;
        border: 1px solid #d8dee8;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>ByteTrack Detection Quality Workbench</h1>
      <section>
        <h2>Run</h2>
        <p>Run id: <code>{manifest["run_id"]}</code></p>
        <p>Suite id: <code>{manifest["run_suite_id"]}</code></p>
        <p>Experiment: <code>{manifest["experiment_id"]}</code></p>
        <p>Config SHA-256: <code>{manifest["config_sha256"]}</code></p>
      </section>
      <section>
        <h2>Scope Guard</h2>
        <p>Interpolated detections: {regression.get("interpolated_detection_count", 0)}</p>
        <p>Regression passed: {regression.get("passed", False)}</p>
        <p>Baseline available: {regression.get("baseline_available", False)}</p>
      </section>
      <section>
        <h2>Open-Source Tracking</h2>
        <p>MLflow: <code>{tracking.get("mlflow", {}).get("path", "not exported")}</code></p>
        <p>DVC: <code>{tracking.get("dvc", {}).get("path", "not exported")}</code></p>
        <p>Evidently: <code>{tracking.get("evidently", {}).get("path", "not exported")}</code></p>
      </section>
      <section>
        <h2>Review Journey</h2>
        <p>Platform manifest: <code>review/platforms.json</code> ({platform_hint}).</p>
        {platform_links}
        <p>Workbench: <a href="{run_page_url}">run page</a></p>
      </section>
      <section>
        <h2>Artifacts</h2>
        <ul>
          <li><code>cleaned/*.json</code></li>
          <li><code>audit/*.jsonl</code></li>
          <li><code>tables/*.parquet</code></li>
          <li><code>report/contact-sheet.html</code></li>
        </ul>
      </section>
      <section>
        <h2>Replay</h2>
        <p><a href=\"../lineage/replay.lock.json\">Replay lock</a></p>
        <p>Open the local workbench and visit <code>{run_page_path}</code>.</p>
      </section>
    </main>
  </body>
</html>
"""

        output = run_root / "report" / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8")
        return output

    def _load_platforms(self, platforms_path: Path) -> dict[str, object]:
        if not platforms_path.exists():
            return {}
        parsed = json.loads(platforms_path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            return {}
        return parsed

    def _platform_links(self, platforms: dict[str, object]) -> str:
        rows = [
            self._platform_row(platforms, key, label)
            for key, label in [
                ("mlflow", "MLflow"),
                ("dvc", "DVC"),
                ("evidently", "Evidently"),
                ("fiftyone", "FiftyOne"),
                ("label_studio", "Label Studio"),
            ]
        ]
        visible_rows = [row for row in rows if row]
        if not visible_rows:
            return ""
        return "<ul>\n" + "\n".join(visible_rows) + "\n        </ul>"

    def _platform_row(self, platforms: dict[str, object], key: str, label: str) -> str:
        raw_status = platforms.get(key)
        if not isinstance(raw_status, dict):
            return ""
        status = escape(str(raw_status.get("status", "unknown")))
        url = raw_status.get("url")
        path = raw_status.get("path")
        if isinstance(url, str) and url:
            target = f'<a href="{escape(url)}">{escape(url)}</a>'
        elif isinstance(path, str) and path:
            target = f"<code>{escape(path)}</code>"
        else:
            target = ""
        return f"          <li>{label}: {status} {target}</li>"
