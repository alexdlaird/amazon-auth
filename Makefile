.PHONY: all local upload

SHELL := /usr/bin/env bash
PYTHON_BIN ?= python

all: local

local:
	@rm -rf *.egg-info dist
	@( \
		$(PYTHON_BIN) -m pip install --upgrade pip && \
		$(PYTHON_BIN) -m pip install --upgrade build && \
		$(PYTHON_BIN) -m build; \
	)

upload: local
	@( \
		$(PYTHON_BIN) -m pip install --upgrade twine && \
		$(PYTHON_BIN) -m twine upload dist/*; \
	)
