.PHONY: bootstrap doctor run check test verify seed migrate clean workbench review-services-up review-services-down

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

test:
	$(PYTHON) -m pytest tests/acceptance -v

verify: check test

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
