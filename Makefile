.PHONY: install test lint format build package clean run docs

PYTHON := python
PIP := $(PYTHON) -m pip

install:
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/

build:
	$(PYTHON) -m build

package:
	$(PYTHON) scripts/package.py

clean:
	$(PYTHON) scripts/package.py --only-zip 2>/dev/null || true
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

run:
	streamlit run app.py

docs:
	@echo "Documentation is in the docs/ directory. No build step configured."
