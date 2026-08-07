from __future__ import annotations

import json
from pathlib import Path


class FiftyOneExporter:
    def export(self, run_root: Path) -> Path:
        manifest = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
        samples = json.loads(
            (run_root / "report" / "sample-manifest.json").read_text(encoding="utf-8")
        )
        output = run_root / "review" / "fiftyone-dataset.json"
        output.write_text(
            json.dumps(
                {
                    "dataset_name": f"handdetect_{manifest['run_suite_id']}_{manifest['run_id']}",
                    "run_suite_id": manifest["run_suite_id"],
                    "run_id": manifest["run_id"],
                    "samples": samples["samples"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return output
