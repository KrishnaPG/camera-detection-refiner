from __future__ import annotations

from handdetect_domain.config import ExperimentConfig, ValidatedExperimentConfig


class ExperimentMatrix:
    def experiments(self, config: ValidatedExperimentConfig) -> tuple[ExperimentConfig, ...]:
        return config.experiments
