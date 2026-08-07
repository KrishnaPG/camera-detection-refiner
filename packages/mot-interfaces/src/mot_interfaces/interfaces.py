from __future__ import annotations

from typing import Protocol

from dq_filter_kit.results import GeometricStageResult, TrackBlock
from handdetect_domain.config import ByteTrackConfig
from vision_columnar.blocks import DetectionBlock


class AssociationAdapter(Protocol):
    def associate(
        self, block: DetectionBlock, geometric: GeometricStageResult, config: ByteTrackConfig
    ) -> TrackBlock: ...
