from __future__ import annotations

import json
from pathlib import Path


class RegressionGateRunner:
    def check(self, run_root: Path, baseline_run_root: Path | None) -> Path:
        evaluation = json.loads((run_root / "evaluation.json").read_text(encoding="utf-8"))
        baseline_available = baseline_run_root is not None and baseline_run_root.exists()
        payload = {
            "passed": evaluation["interpolated_detection_count"] == 0,
            "baseline_available": baseline_available,
            "interpolated_detection_count": evaluation["interpolated_detection_count"],
            "raw_detection_count": evaluation["raw_detection_count"],
            "cleaned_detection_count": evaluation["cleaned_detection_count"],
        }
        if baseline_available and baseline_run_root is not None:
            baseline = json.loads(
                (baseline_run_root / "evaluation.json").read_text(encoding="utf-8")
            )
            payload["baseline_run_root"] = str(baseline_run_root)
            payload["metric_deltas"] = {
                "raw_detection_count": (
                    evaluation["raw_detection_count"] - baseline["raw_detection_count"]
                ),
                "cleaned_detection_count": (
                    evaluation["cleaned_detection_count"] - baseline["cleaned_detection_count"]
                ),
                "rejected_detection_count": (
                    evaluation["rejected_detection_count"] - baseline["rejected_detection_count"]
                ),
            }
        output = run_root / "regression.json"
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output
