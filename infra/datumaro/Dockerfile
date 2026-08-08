FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/datumaro-venv \
    PATH="/opt/datumaro-venv/bin:${PATH}"

WORKDIR /srv/datumaro-exporter

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
  && python -m venv /opt/datumaro-venv \
  && /opt/datumaro-venv/bin/pip install --upgrade pip \
  && /opt/datumaro-venv/bin/pip install --no-cache-dir \
    datumaro==1.13.0 \
    numpy==2.2.6 \
    opencv-python-headless==4.12.0.88 \
    pyarrow==24.0.0 \
  && groupadd --gid 1000 handdetect \
  && useradd --uid 1000 --gid 1000 --home-dir /tmp/handdetect/home --shell /usr/sbin/nologin handdetect \
  && rm -rf /var/lib/apt/lists/*

COPY exporter_server.py /srv/datumaro-exporter/exporter_server.py

USER handdetect

CMD ["python", "/srv/datumaro-exporter/exporter_server.py"]
