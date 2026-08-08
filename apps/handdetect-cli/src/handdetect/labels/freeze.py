from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path


class LabelSetFreezer:
    def freeze_tasks(
        self,
        source: Path,
        output_root: Path | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> Path:
        payload = source.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        label_root = (output_root or source.parent / "labels" / "versions") / digest
        label_root.mkdir(parents=True, exist_ok=True)
        output = label_root / "manifest.json"
        frozen_manifest = {
            "label_set_id": digest,
            "annotation_sha256": digest,
            "source": str(source),
            "metadata": dict(metadata or {}),
        }
        output.write_text(json.dumps(frozen_manifest, indent=2), encoding="utf-8")
        return output
