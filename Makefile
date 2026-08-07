.PHONY: bootstrap doctor run check typecheck test verify seed migrate clean workbench review-services-up review-services-down

PYTHON ?= python
CONFIG ?= configs/default-experiments.toml

bootstrap:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

doctor:
	$(PYTHON) -m handdetect.cli.main doctor

run:
	$(PYTHON) -m handdetect.cli.main run --config $(CONFIG)

check:
	$(PYTHON) -m ruff format --check packages apps tests
	$(PYTHON) -m ruff check packages apps tests

typecheck:
	$(PYTHON) -m mypy \
		packages/dq-contracts/src \
		packages/handdetect-domain/src \
		packages/dq-resources/src \
		packages/experiment-tracking/src/experiment_tracking/interfaces.py \
		packages/experiment-tracking/src/experiment_tracking/export_status.py \
		apps/handdetect-cli/src/handdetect/lineage/models.py

test:
	$(PYTHON) -m pytest tests/acceptance -v

verify: check typecheck test

seed:
	$(PYTHON) -m handdetect.cli.main seed --data-root data

migrate:
	$(PYTHON) -m handdetect.cli.main migrate

clean:
	$(PYTHON) -m handdetect.cli.main clean

workbench:
	$(PYTHON) -m handdetect.cli.main workbench serve

review-services-up:
	docker compose up -d

review-services-down:
	docker compose down
