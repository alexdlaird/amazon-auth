.PHONY: all install nopyc clean test test-integration test-integration-sites download-integration-output docs check generate-region-data local validate-release install-waf install-browser

SHELL := /usr/bin/env bash
PYTHON_BIN ?= python
PROJECT_VENV ?= venv
INTEGRATION_TEST_RERUN ?= 2
INTEGRATION_TEST_RERUN_DELAY ?= 300
INTEGRATION_TEST_FAIL_FAST ?= false
PYTEST_EXTRA_ARGS ?=
INTEGRATION_OUTPUT_DIR ?= build/integration-test-output
INTEGRATION_RUN_ID ?= $(shell gh run list --workflow integration.yml --limit 1 --json databaseId --jq '.[0].databaseId')
SSH_KEY ?= ~/.ssh/id_rsa

WAF_EXTRAS := capsolver,anticaptcha,2captcha

all: local check test

venv:
	$(PYTHON_BIN) -m pip install virtualenv --user
	$(PYTHON_BIN) -m virtualenv $(PROJECT_VENV)

install: venv
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install .; \
	)

install-waf:
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[$(WAF_EXTRAS)]"; \
	)

install-browser:
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[browser]"; \
		playwright install chromium --with-deps; \
	)

nopyc:
	find . -name '*.pyc' | xargs rm -f || true
	find . -name __pycache__ | xargs rm -rf || true

clean: nopyc
	rm -rf build dist *.egg-info $(PROJECT_VENV)

test: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[dev]"; \
		coverage run -m pytest -v --ignore=tests/integration -o junit_suite_name=unit && coverage report && coverage xml && coverage html; \
	)

test-integration: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[dev,integration]"; \
		pytest -v tests/integration --ignore=tests/integration/test_integration_sites.py -o junit_suite_name=integration --reruns ${INTEGRATION_TEST_RERUN} --reruns-delay ${INTEGRATION_TEST_RERUN_DELAY} $(if $(filter true,${INTEGRATION_TEST_FAIL_FAST}),-x) ${PYTEST_EXTRA_ARGS}; \
	)

test-integration-sites: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[dev,integration]"; \
		pytest -v -rs tests/integration/test_integration_sites.py -o junit_suite_name=integration-sites ${PYTEST_EXTRA_ARGS}; \
	)

download-integration-output:
	@( \
		rm -rf $(INTEGRATION_OUTPUT_DIR) && \
		gh run download $(INTEGRATION_RUN_ID) -n integration-test-output -D $(INTEGRATION_OUTPUT_DIR) && \
		age -d -i $(SSH_KEY) $(INTEGRATION_OUTPUT_DIR)/integration-test-output.tar.gz.age | tar xzf - -C $(INTEGRATION_OUTPUT_DIR) && \
		rm $(INTEGRATION_OUTPUT_DIR)/integration-test-output.tar.gz.age && \
		echo "Integration test output from run $(INTEGRATION_RUN_ID) is in $(INTEGRATION_OUTPUT_DIR)"; \
	)

docs: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[docs]"; \
		sphinx-build -M html docs build/docs -n -E; \
	)

check: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[dev]"; \
		mypy amazonauth && flake8; \
	)

generate-region-data: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python scripts/generate-region-data.py; \
	)

local:
	@rm -rf *.egg-info dist
	@( \
		$(PYTHON_BIN) -m pip install --upgrade pip && \
		$(PYTHON_BIN) -m pip install --upgrade build && \
		$(PYTHON_BIN) -m build && \
		$(PYTHON_BIN) -m pip install "$$(ls dist/*.tar.gz)"; \
	)

validate-release:
	@if [[ "${VERSION}" == "" ]]; then echo "VERSION is not set"; exit 1 ; fi

	@if [[ $$(grep "__version__ = \"${VERSION}\"" amazonauth/__init__.py) == "" ]] ; then echo "Version not bumped in amazonauth/__init__.py"; exit 1 ; fi

	@if [ -f SECURITY.md ]; then \
		MAJOR_MINOR=$$(echo "${VERSION}" | cut -d. -f1-2); \
		if [[ $$(grep "| $${MAJOR_MINOR}\.x" SECURITY.md) == "" ]] ; then echo "SECURITY.md missing supported-versions entry for $${MAJOR_MINOR}.x"; exit 1 ; fi; \
	fi
