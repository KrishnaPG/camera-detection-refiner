FROM python:3.12-slim AS wheel-builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/handdetect-wheel-venv \
    PATH="/opt/handdetect-wheel-venv/bin:$PATH"

WORKDIR /build

COPY pyproject.toml /build/pyproject.toml
COPY README.md /build/README.md
COPY Makefile /build/Makefile
COPY apps /build/apps
COPY packages /build/packages

RUN python -m venv "$VIRTUAL_ENV" \
  && pip install --upgrade pip \
  && pip wheel --wheel-dir /wheels /build

FROM python:3.12-slim

ARG HANDDETECT_BUILD_COMMIT=local-image

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/handdetect-venv \
    PATH="/opt/handdetect-venv/bin:$PATH" \
    PYTHONPATH="/workspace/external/biodock/src" \
    HANDDETECT_BUILD_COMMIT=${HANDDETECT_BUILD_COMMIT}

WORKDIR /workspace

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    ffmpeg \
  && groupadd --gid 1000 handdetect \
  && useradd --uid 1000 --gid 1000 --home-dir /tmp/handdetect/home --shell /usr/sbin/nologin handdetect \
  && rm -rf /var/lib/apt/lists/*

COPY --from=wheel-builder /wheels /wheels

RUN python -m venv "$VIRTUAL_ENV" \
  && pip install --upgrade pip \
  && pip install --no-index --find-links=/wheels handdetect-quality \
  && rm -rf /wheels

COPY pyproject.toml /workspace/pyproject.toml
COPY README.md /workspace/README.md
COPY Makefile /workspace/Makefile
COPY configs /workspace/configs
COPY external/biodock/src /workspace/external/biodock/src
COPY generator-package /workspace/generator-package
COPY labels /workspace/labels
