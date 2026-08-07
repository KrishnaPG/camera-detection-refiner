from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from dq_contracts.ids import ExperimentId, RunId, RunSuiteId


class RunSuiteIdProvider:
    def create(self) -> RunSuiteId:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        return RunSuiteId(f"suite-{timestamp}")


class RunIdProvider:
    def create(
        self, suite_id: RunSuiteId, experiment_id: ExperimentId, config_sha256: str
    ) -> RunId:
        digest = hashlib.sha256(f"{suite_id}:{experiment_id}:{config_sha256}".encode()).hexdigest()[
            :16
        ]
        return RunId(f"{experiment_id}-{digest}")
