from __future__ import annotations

from dq_contracts.enums import RunEvent, RunState

TRANSITIONS: dict[tuple[RunState, RunEvent], RunState] = {
    (RunState.CREATED, RunEvent.SCAN_OK): RunState.DATASET_SCANNED,
    (RunState.DATASET_SCANNED, RunEvent.CLIP_STARTED): RunState.CLIPS_RUNNING,
    (RunState.CLIPS_RUNNING, RunEvent.CLIP_SUCCEEDED): RunState.CLIPS_RUNNING,
    (RunState.CLIPS_RUNNING, RunEvent.ALL_CLIPS_SUCCEEDED): RunState.ARTIFACTS_WRITTEN,
    (RunState.ARTIFACTS_WRITTEN, RunEvent.EVAL_SUCCEEDED): RunState.EVALUATED,
    (RunState.EVALUATED, RunEvent.REPORT_SUCCEEDED): RunState.REPORTED,
    (RunState.REPORTED, RunEvent.REGRESSION_SUCCEEDED): RunState.REGRESSION_CHECKED,
    (RunState.REGRESSION_CHECKED, RunEvent.ALL_CLIPS_SUCCEEDED): RunState.COMPLETE,
}


class RunStateMachine:
    def __init__(self) -> None:
        self.state = RunState.CREATED

    def apply(self, event: RunEvent) -> RunState:
        if event == RunEvent.FAILURE_SEEN:
            self.state = RunState.FAILED
            return self.state
        if event == RunEvent.CANCEL_REQUESTED:
            self.state = RunState.CANCELLED
            return self.state

        key = (self.state, event)
        if key not in TRANSITIONS:
            raise ValueError(f"invalid run transition: {self.state} + {event}")
        self.state = TRANSITIONS[key]
        return self.state
