from __future__ import annotations

from typing import NewType

ClipId = NewType("ClipId", str)
RunSuiteId = NewType("RunSuiteId", str)
RunId = NewType("RunId", str)
ExperimentId = NewType("ExperimentId", str)
MlflowRunId = NewType("MlflowRunId", str)
LabelSetId = NewType("LabelSetId", str)
DetectionId = NewType("DetectionId", str)
TrackId = NewType("TrackId", int)
FrameIndex = NewType("FrameIndex", int)
TimestampNs = NewType("TimestampNs", int)
