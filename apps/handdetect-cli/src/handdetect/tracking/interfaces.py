from __future__ import annotations

from typing import Protocol

from handdetect.filters.results import GeometricStageResult, TrackBlock
from handdetect.hotpath.blocks import DetectionBlock
from handdetect_domain.config import ByteTrackConfig


class AssociationAdapter(Protocol):
    def associate(
        self, block: DetectionBlock, geometric: GeometricStageResult, config: ByteTrackConfig
    ) -> TrackBlock: ...
