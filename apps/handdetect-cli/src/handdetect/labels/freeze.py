from __future__ import annotations

import hashlib
import json
from pathlib import Path


class LabelSetFreezer:
    def freeze_tasks(self, source: Path) -> Path:
        payload = source.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        label_root = Path("labels") / "versions" / digest
        label_root.mkdir(parents=True, exist_ok=True)
        output = label_root / "manifest.json"
        output.write_text(
            json.dumps(
                {"label_set_id": digest, "annotation_sha256": digest, "source": str(source)},
                indent=2,
            ),
            encoding="utf-8",
        )
        return output
