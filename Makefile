SHELL := /bin/bash

# ===== Config =====
VENV ?= venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
RUFF := $(VENV)/bin/ruff
BLACK := $(VENV)/bin/black
PYTEST := $(VENV)/bin/pytest
APP ?= app.main:app

IMAGE ?= fussballde-machtkalender-scraper-api:latest
CONTAINER ?= fussballde-machtkalender-scraper-api

# default target
.DEFAULT_GOAL := help

# ===== Helpers =====
.PHONY: help
help:
	@echo "Targets:"
	@echo "  venv             Create virtual env in ./$(VENV)"
	@echo "  install          Install dependencies from requirements.txt (into venv)"
	@echo "  freeze           Freeze current deps to requirements.txt"
	@echo "  run              Run API locally (uvicorn --reload)"
	@echo "  dev              Alias for run"
	@echo "  shell            Open interactive shell with venv activated"
	@echo "  lint             Run ruff (linter)"
	@echo "  format           Run black (formatter)"
	@echo "  test             Run pytest"
	@echo "  clean            Remove caches/build artifacts"
	@echo "  docker-build     Build docker image ($(IMAGE))"
	@echo "  docker-run       Run docker image on :8000"
	@echo "  compose-up       docker compose up -d"
	@echo "  compose-down     docker compose down"

# ===== Python env / deps =====
$(VENV)/bin/python:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -U pip

.PHONY: venv
venv: $(VENV)/bin/python

.PHONY: install
install: venv
	$(PIP) install -r requirements.txt

.PHONY: freeze
freeze: venv
	$(PIP) freeze > requirements.txt

# ===== Run / Dev =====
.PHONY: run dev
run dev: install
	$(UVICORN) $(APP) --reload

# Start an interactive shell with venv activated
.PHONY: shell
shell: venv
	@echo "Activating venv in a subshell. Exit with 'exit'."
	@bash -i -c "source $(VENV)/bin/activate && exec bash -i"

# ===== QA =====
.PHONY: lint
lint: install
	$(RUFF) check .

.PHONY: format
format: install
	$(BLACK) .

.PHONY: test
test: install
	$(PYTEST) -q

# ===== Clean =====
.PHONY: clean
clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov coverage.xml
	find . -name '*.pyc' -delete -o -name '*.pyo' -delete

# ===== Docker =====
.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE) .

.PHONY: docker-run
docker-run:
	docker run --rm -p 8000:8000 --name $(CONTAINER) $(IMAGE)

# ===== Compose =====
.PHONY: compose-up
compose-up:
	docker compose up -d

.PHONY: compose-down
compose-down:
	docker compose down
