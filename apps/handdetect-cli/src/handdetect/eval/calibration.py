from __future__ import annotations

from pathlib import Path


class CalibrationSweepRunner:
    def write_empty_sweep(self, run_root: Path) -> Path:
        output = run_root / "calibration.json"
        output.write_text(
            '{"sweep":[],"note":"false-negative interpolation is disabled"}\n', encoding="utf-8"
        )
        return output
