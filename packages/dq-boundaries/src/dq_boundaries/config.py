from __future__ import annotations

import tomllib
from pathlib import Path

from handdetect_domain.config import ValidatedExperimentConfig
from pydantic import ValidationError


class ConfigParseError(RuntimeError):
    def __init__(self, path: Path, cause: ValidationError | OSError) -> None:
        super().__init__(f"failed to parse experiment config at {path}: {cause}")
        self.path = path
        self.cause = cause


class ExperimentConfigParser:
    def parse_path(self, path: Path) -> ValidatedExperimentConfig:
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
            return ValidatedExperimentConfig.model_validate(payload)
        except (ValidationError, OSError, ValueError) as exc:
            raise ConfigParseError(path, exc) from exc
