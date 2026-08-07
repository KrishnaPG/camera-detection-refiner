from __future__ import annotations

import tomllib
from pathlib import Path

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

    assert str(label_studio.specifier) == "==2.1.0"
    assert fiftyone.specifier.contains(Version("0.25.2"))
    assert not fiftyone.specifier.contains(Version("1.20.1"))
    assert numpy.specifier.contains(Version("2.2.6"))
    assert not numpy.specifier.contains(Version("2.5.1"))
    assert opencv.specifier.contains(Version("4.12.0.88"))
    assert not opencv.specifier.contains(Version("5.0.0.93"))


def test_dockerfile_installs_git_for_lineage_capture() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "apt-get install -y --no-install-recommends" in dockerfile
    assert "\n    git \\\n" in dockerfile or "\n    git\n" in dockerfile


def test_default_configs_route_runtime_state_to_tmp() -> None:
    for path in [
        ROOT / "configs" / "default-experiments.toml",
        ROOT / "configs" / "smoke-experiment.toml",
    ]:
        runtime = tomllib.loads(path.read_text(encoding="utf-8"))["runtime"]
        assert runtime["mlflow_tracking_uri"] == "/tmp/handdetect/mlruns"
        assert runtime["dvclive_root"] == "/tmp/handdetect/dvclive"


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


def test_compose_prepares_tmp_state_then_drops_to_host_uid() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "HANDDETECT_COMPOSE_UID" in compose
    assert "HANDDETECT_COMPOSE_GID" in compose
    assert "chown -R" in compose
    assert "USER=handdetect" in compose
    assert "LOGNAME=handdetect" in compose
    assert "setpriv --reuid" in compose


def test_dockerfile_marks_workspace_as_git_safe_directory() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "git config --system --add safe.directory /workspace" in dockerfile


def test_docker_image_defines_non_root_runtime_user() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "groupadd --gid 1000 handdetect" in dockerfile
    assert "useradd --uid 1000 --gid 1000" in dockerfile
