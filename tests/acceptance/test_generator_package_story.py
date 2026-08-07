from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_generator_package_uses_biodock_video_review_layout() -> None:
    workspace = json.loads(
        (ROOT / "generator-package" / "ui" / "workspace.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (ROOT / "generator-package" / "generator-package-manifest.json").read_text(encoding="utf-8")
    )
    default_layout = next(
        layout
        for layout in workspace["layouts"]
        if layout["layoutId"] == workspace["defaultLayoutId"]
    )

    assert manifest["metadata"]["package_id"] == "handdetect_quality_adapter"
    assert workspace["workspaceId"] == "handdetect_quality_story"
    assert default_layout["extends"] == "berg10.generator.videoReview"
    assert default_layout["slots"]["slot.history"] == ["handdetect_timeline"]
    assert "handdetect.run_smoke_experiment" in {
        action["action_id"] for action in manifest["actions"]
    }


def test_generator_package_descriptor_is_sdk_generated() -> None:
    result = subprocess.run(
        ["python", "scripts/build_handdetect_generator_package.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    diff = subprocess.run(
        [
            "git",
            "diff",
            "--exit-code",
            "--",
            "generator-package/generator-package-manifest.json",
            "generator-package/ui/workspace.json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert diff.returncode == 0, diff.stdout + diff.stderr
