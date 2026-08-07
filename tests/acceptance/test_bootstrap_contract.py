from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from handdetect.runs.retention import RuntimeRetentionPruner
from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_declares_label_studio_compatible_opencv_pin() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    requirements = {Requirement(item).name: Requirement(item) for item in project["dependencies"]}
    opencv = requirements["opencv-python-headless"]
    label_studio = requirements["label-studio-sdk"]
    fiftyone = requirements["fiftyone"]
    numpy = requirements["numpy"]
    plotly = requirements["plotly"]
    starlette = requirements["starlette"]

    assert str(label_studio.specifier) == "==2.1.0"
    assert fiftyone.specifier.contains(Version("0.25.2"))
    assert not fiftyone.specifier.contains(Version("1.20.1"))
    assert numpy.specifier.contains(Version("2.2.6"))
    assert not numpy.specifier.contains(Version("2.5.1"))
    assert plotly.specifier.contains(Version("5.24.1"))
    assert starlette.specifier.contains(Version("0.46.2"))
    assert opencv.specifier.contains(Version("4.12.0.88"))
    assert not opencv.specifier.contains(Version("5.0.0.93"))


def test_dockerfile_uses_build_commit_instead_of_runtime_git() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "ARG HANDDETECT_BUILD_COMMIT" in dockerfile
    assert "HANDDETECT_BUILD_COMMIT=${HANDDETECT_BUILD_COMMIT}" in dockerfile
    assert "\n    git \\\n" not in dockerfile
    assert "AS wheel-builder" in dockerfile
    assert "pip wheel --wheel-dir /wheels /build" in dockerfile
    assert "pip install --no-index --find-links=/wheels handdetect-quality" in dockerfile
    assert "pip install -e" not in dockerfile
    assert "COPY pyproject.toml /workspace/pyproject.toml" in dockerfile


def test_dockerignore_only_excludes_root_runtime_dirs() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "\n/runs\n" in dockerignore
    assert "\n/mlruns\n" in dockerignore
    assert "\n/dvclive\n" in dockerignore
    assert "\nruns\n" not in dockerignore


def test_gitignore_only_excludes_root_runtime_dirs() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    gitignore_lines = gitignore.splitlines()
    assert "/data" in gitignore_lines
    assert "/runs" in gitignore_lines
    assert "/mlruns" in gitignore_lines
    assert "data" not in gitignore_lines
    assert "runs" not in gitignore_lines


def test_default_configs_route_runtime_state_to_tmp() -> None:
    for path in [
        ROOT / "configs" / "default-experiments.toml",
        ROOT / "configs" / "smoke-experiment.toml",
    ]:
        runtime = tomllib.loads(path.read_text(encoding="utf-8"))["runtime"]
        assert runtime["runs_root"] == "/tmp/handdetect/runs"
        assert runtime["mlflow_tracking_uri"] == "/tmp/handdetect/mlruns"
        assert runtime["dvclive_root"] == "/tmp/handdetect/dvclive"
        assert runtime["evidently_root"] == "/tmp/handdetect/evidently"


def test_repo_does_not_depend_on_root_sitecustomize_hack() -> None:
    assert not (ROOT / "sitecustomize.py").exists()
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "sitecustomize.py" not in dockerfile
    lineage_capture = (
        ROOT / "apps" / "handdetect-cli" / "src" / "handdetect" / "lineage" / "capture.py"
    ).read_text(encoding="utf-8")
    assert "sitecustomize.py" not in lineage_capture


def test_compose_shares_tmp_runtime_state_across_services() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "file:/tmp/handdetect/mlruns" in compose
    assert "- /tmp/handdetect:/tmp/handdetect" in compose


def test_compose_starts_review_platform_infra() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "fiftyone-mongo:" in compose
    assert "mongo:7.0.15" in compose
    assert "mongod --quiet --dbpath /data/db --bind_ip_all" in compose
    assert "condition: service_healthy" in compose
    assert "mongosh --quiet --eval" in compose
    assert "fiftyone:" in compose
    assert "fiftyone app launch --address 0.0.0.0 --port 5151 --remote --wait -1" in compose
    assert "FIFTYONE_DATABASE_URI" in compose
    assert "HANDDETECT_FIFTYONE_PUBLIC_URL" in compose
    assert "/tmp/handdetect-services/fiftyone-mongo:/data/db" in compose
    assert "HANDDETECT_SERVICE_STATE_MAX_AGE_DAYS" in compose
    assert "find /data/db -mindepth 1 -maxdepth 1 -mtime" in compose
    assert "label-studio:" in compose
    assert "heartexlabs/label-studio:1.21.0" in compose
    assert "/tmp/handdetect-services/label-studio:/label-studio/data" in compose
    assert "find /label-studio/data -mindepth 1 -maxdepth 1 -mtime" in compose
    assert "HANDDETECT_LABEL_STUDIO_URL" in compose
    assert "HANDDETECT_LABEL_STUDIO_PUBLIC_URL" in compose
    assert "LABEL_STUDIO_USER_TOKEN" in compose
    assert '"8080:8080"' in compose


def test_default_compose_does_not_source_mount_repo() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "- .:/workspace" not in compose
    assert "./data:/workspace/data:ro" in compose


def test_runtime_retention_prunes_old_generated_suites(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    old_suite = runs_root / "suite-old"
    protected_suite = runs_root / "suite-current"
    old_suite.mkdir(parents=True)
    protected_suite.mkdir(parents=True)
    (old_suite / "blob.bin").write_bytes(b"x" * 64)
    (protected_suite / "blob.bin").write_bytes(b"x" * 64)

    result = RuntimeRetentionPruner(
        max_bytes=1,
        min_free_bytes=0,
        keep_suites=1,
    ).prune(runs_root, protect=(protected_suite,))

    assert old_suite in result.removed_paths
    assert not old_suite.exists()
    assert protected_suite.exists()


def test_runtime_retention_keep_suites_counts_protected_suite(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    oldest_suite = runs_root / "suite-001"
    newer_suite = runs_root / "suite-002"
    protected_suite = runs_root / "suite-003"
    for suite in (oldest_suite, newer_suite, protected_suite):
        suite.mkdir(parents=True)

    result = RuntimeRetentionPruner(
        max_bytes=1024 * 1024,
        min_free_bytes=0,
        keep_suites=2,
    ).prune(runs_root, protect=(protected_suite,))

    assert oldest_suite in result.removed_paths
    assert not oldest_suite.exists()
    assert newer_suite.exists()
    assert protected_suite.exists()


def test_repo_workspace_has_no_generated_runtime_dirs() -> None:
    generated = ["runs", "dvclive", "mlruns", ".handdetect"]
    present = [path for path in generated if (ROOT / path).exists()]
    assert present == []


def test_repo_tracks_imported_handdetect_internal_packages() -> None:
    source_root = ROOT / "apps" / "handdetect-cli" / "src" / "handdetect"
    tracked_targets = [
        path.relative_to(ROOT).as_posix()
        for package in ("runs", "labels")
        for path in sorted((source_root / package).glob("*.py"))
    ]
    assert tracked_targets
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", *tracked_targets],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_repo_tracks_runtime_label_assets_used_by_cli_and_dockerfile() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY labels /workspace/labels" in dockerfile
    tracked_targets = [
        "labels/README.md",
        "labels/versions/empty-gold-v1/manifest.json",
    ]
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", *tracked_targets],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_compose_prepares_tmp_state_then_drops_to_host_uid() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "HANDDETECT_COMPOSE_UID" in compose
    assert "HANDDETECT_COMPOSE_GID" in compose
    assert "chown -R" in compose
    assert 'chown "$$HANDDETECT_COMPOSE_UID:$$HANDDETECT_COMPOSE_GID" /tmp/handdetect' in compose
    assert (
        'chown -R "$$HANDDETECT_COMPOSE_UID:$$HANDDETECT_COMPOSE_GID" /tmp/handdetect'
        not in compose
    )
    assert "/tmp/handdetect/replays" in compose
    assert "USER=handdetect" in compose
    assert "LOGNAME=handdetect" in compose
    assert "setpriv --reuid" in compose
    assert "HANDDETECT_SELECTED_DATA_SNAPSHOT_MAX_BYTES" in compose


def test_label_studio_compose_enables_token_and_recovers_generated_sqlite_state() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "LABEL_STUDIO_USER_TOKEN" in compose
    assert "--enable-legacy-api-token" in compose
    assert "legacy_api_tokens_enabled=True" in compose
    assert "resetting generated Label Studio SQLite state after local migration failure" in compose
    assert "rm -f /label-studio/data/label_studio.sqlite3" in compose


def test_dockerfile_does_not_require_runtime_git_safe_directory() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "git config --system --add safe.directory /workspace" not in dockerfile


def test_docker_image_defines_non_root_runtime_user() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "groupadd --gid 1000 handdetect" in dockerfile
    assert "useradd --uid 1000 --gid 1000" in dockerfile
