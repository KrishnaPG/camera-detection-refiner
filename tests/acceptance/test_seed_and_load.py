from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED_MANIFEST = ROOT / "runs" / "seed" / "seed-manifest.json"


def test_seed_manifest_uses_real_dataset_clips() -> None:
    result = subprocess.run(
        [
            "python",
            "-m",
            "handdetect.cli.main",
            "seed",
            "--data-root",
            "data",
            "--out",
            str(SEED_MANIFEST),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(SEED_MANIFEST.read_text(encoding="utf-8"))
    assert payload["dataset_file_count"] == 235
    assert payload["clip_count"] == 39
    assert "0c54a47b_t010" in payload["smoke_clip_ids"]
