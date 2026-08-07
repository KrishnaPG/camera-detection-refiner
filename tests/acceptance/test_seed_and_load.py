from __future__ import annotations

import json
import subprocess
from pathlib import Path

from handdetect.runtime_paths import runs_root

ROOT = Path(__file__).resolve().parents[2]


def test_seed_manifest_uses_real_dataset_clips() -> None:
    result = subprocess.run(
        [
            "python",
            "-m",
            "handdetect.cli.main",
            "seed",
            "--data-root",
            "data",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    seed_manifest = runs_root() / "seed" / "seed-manifest.json"
    payload = json.loads(seed_manifest.read_text(encoding="utf-8"))
    assert payload["dataset_file_count"] == 235
    assert payload["clip_count"] == 39
    assert "0c54a47b_t010" in payload["smoke_clip_ids"]
