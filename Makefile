install:
	python -m pip install -e .

test:
	python -m pytest

lint:
	python -m ruff check .
