FROM python:3.12-slim

ARG HANDDETECT_BUILD_COMMIT=local-image

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
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
  && groupadd --gid 1000 handdetect \
  && useradd --uid 1000 --gid 1000 --home-dir /tmp/handdetect/home --shell /usr/sbin/nologin handdetect \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /workspace/pyproject.toml
COPY README.md /workspace/README.md
COPY Makefile /workspace/Makefile
COPY apps /workspace/apps
COPY packages /workspace/packages
COPY configs /workspace/configs
COPY labels /workspace/labels

RUN pip install --upgrade pip \
  && pip install -e /workspace
