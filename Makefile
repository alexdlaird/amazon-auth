.PHONY: all local

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

