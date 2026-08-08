from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIODOCK_SRC = ROOT / "external" / "biodock" / "src"
if str(BIODOCK_SRC) not in sys.path:
    sys.path.insert(0, str(BIODOCK_SRC))

from biodock.generator_sdk.package_authoring import (  # noqa: E402
    GeneratorPackageBundleSpec,
    PackageActionOutputSpec,
    PackageActionSpec,
    PackageActivationSpec,
    PackageImplementationSpec,
    PackageMetadataSpec,
    PackageWorkspaceSpec,
    RawAdmissionSpec,
    ViewSpec,
    WorkspaceLayoutSpec,
    WorkspacePanelSpec,
    WorkspaceThemeSpec,
)


def handdetect_generator_package_bundle() -> GeneratorPackageBundleSpec:
    return GeneratorPackageBundleSpec(
        manifest_schema_path=(
            "../external/biodock/external/berg10-state-server/schemas/berg10/"
            "berg10-generator-package-manifest.schema.json"
        ),
        metadata=PackageMetadataSpec(
            package_id="handdetect_quality_adapter",
            alias="handdetect",
            version="2026.08.08",
            display_name="HandDetect Quality Adapter",
            generator_id="handdetect-quality-adapter",
        ),
        activation=PackageActivationSpec(
            source_kind="handdetect_quality_run",
            producer_id="handdetect-quality-adapter",
            producer_versions=(">=2026.08.08 <2027.0.0",),
        ),
        implementation=PackageImplementationSpec(
            language="python",
            module="handdetect.cli.main",
            host_entrypoint="handdetect",
        ),
        actions=(
            PackageActionSpec(
                action_id="handdetect.run_smoke_experiment",
                title="Run smoke experiment",
                description=(
                    "Run the HandDetect smoke experiment and publish run-scoped visual "
                    "review artifacts."
                ),
                outputs=(
                    PackageActionOutputSpec(
                        role="handdetect_story_projection",
                        kind="c_view",
                        view_id="handdetect_story_runs_v1",
                    ),
                    PackageActionOutputSpec(
                        role="handdetect_review_artifacts",
                        kind="artifact",
                    ),
                ),
            ),
        ),
        raw_admissions=(
            RawAdmissionSpec(
                schema="schemas/handdetect-run-event.schema.json",
                families=("b_runtime_status", "b_artifact"),
            ),
        ),
        views=(ViewSpec(sql="views/handdetect_story_views.sql"),),
        workspace=_workspace_spec(),
    )


def _workspace_spec() -> PackageWorkspaceSpec:
    return PackageWorkspaceSpec(
        workspaceId="handdetect_quality_story",
        defaultLayoutId="handdetect_customer_demo_console",
        selectorGroupLabel="HandDetect",
        theme=WorkspaceThemeSpec(
            skinPackId="handdetect-forensic-workbench",
            overrideCssPath="ui/themes/handdetect-story.overrides.css",
        ),
        panels=_panels(),
        layouts=_layouts(),
    )


def _panels() -> tuple[WorkspacePanelSpec, ...]:
    return (
        _panel("handdetect_story_header", "Story Header", "handdetect_story_runs_v1"),
        _panel("handdetect_clip_navigator", "Clip Navigator", "handdetect_story_clips_v1"),
        _panel(
            "handdetect_rejection_taxonomy",
            "Rejection Taxonomy",
            "handdetect_story_rejections_v1",
        ),
        _panel(
            "handdetect_synchronized_viewer",
            "Synchronized Viewer",
            "handdetect_story_viewer_v1",
            app_panel="biodock.externalReviewFrame",
        ),
        _panel("handdetect_decision_inspector", "Decision Inspector", "handdetect_story_events_v1"),
        _panel("handdetect_track_explorer", "Track Explorer", "handdetect_story_tracks_v1"),
        _panel("handdetect_timeline", "Timeline", "handdetect_story_timeline_v1"),
        WorkspacePanelSpec(
            panelId="handdetect_platform_bridge",
            title="Platform Bridge",
            viewId="handdetect_story_platforms_v1",
            appPanel="biodock.generatorArtifacts",
        ),
        _panel("handdetect_diagnostics", "Diagnostics", "handdetect_story_diagnostics_v1"),
    )


def _panel(
    panel_id: str,
    title: str,
    view_id: str,
    *,
    app_panel: str = "biodock.cViewPanel",
) -> WorkspacePanelSpec:
    return WorkspacePanelSpec(
        panelId=panel_id,
        title=title,
        viewId=view_id,
        appPanel=app_panel,
    )


def _layouts() -> tuple[WorkspaceLayoutSpec, ...]:
    return (
        WorkspaceLayoutSpec(
            layoutId="handdetect_customer_demo_console",
            label="Customer Demo Console",
            category="review",
            description=(
                "Frame-synchronized raw detector versus adapter output, with MOT tracks "
                "and decision explanations visible in the first viewport."
            ),
            audience=(
                "Evaluator, customer, or reviewer validating HandDetect false-positive "
                "handling visually."
            ),
            bestFor=(
                "Demoing the adapter value, showing ByteTrack continuity, and jumping "
                "through rejection categories."
            ),
            useWhen="Use for smoke-run review, customer demos, and first-pass visual QA.",
            avoidWhen=(
                "Avoid for annotation batch correction; use Annotation Handoff once "
                "CVAT is configured."
            ),
            extends="berg10.generator.videoReview",
            slots={
                "slot.status": ("handdetect_story_header",),
                "slot.review": ("handdetect_clip_navigator", "handdetect_rejection_taxonomy"),
                "slot.primary": ("handdetect_synchronized_viewer",),
                "slot.inspector": ("handdetect_decision_inspector", "handdetect_track_explorer"),
                "slot.history": ("handdetect_timeline",),
                "slot.artifacts": ("handdetect_platform_bridge",),
                "slot.diagnostics": ("handdetect_diagnostics",),
            },
        ),
        WorkspaceLayoutSpec(
            layoutId="handdetect_forensic_review_bay",
            label="Forensic Review Bay",
            category="debug",
            extends="berg10.generator.debug",
            slots={
                "slot.status": ("handdetect_story_header",),
                "slot.primary": ("handdetect_synchronized_viewer",),
                "slot.debug": ("handdetect_rejection_taxonomy",),
                "slot.audit": ("handdetect_decision_inspector",),
                "slot.history": ("handdetect_timeline",),
                "slot.diagnostics": ("handdetect_diagnostics",),
            },
        ),
        WorkspaceLayoutSpec(
            layoutId="handdetect_annotation_handoff",
            label="Annotation Handoff",
            category="review",
            extends="berg10.generator.review",
            slots={
                "slot.review": ("handdetect_rejection_taxonomy",),
                "slot.reviewDetail": (
                    "handdetect_synchronized_viewer",
                    "handdetect_decision_inspector",
                ),
                "slot.artifacts": ("handdetect_platform_bridge",),
                "slot.history": ("handdetect_timeline",),
            },
        ),
    )


def main() -> None:
    package_root = ROOT / "generator-package"
    handdetect_generator_package_bundle().write_descriptor_files(package_root)


if __name__ == "__main__":
    main()
