install:
	python -m pip install -e .

test:
	python -m pytest

lint:
	python -m ruff check .

bootstrap:
	./scripts/install.sh

bootstrap-windows:
	powershell -ExecutionPolicy Bypass -File scripts/install.ps1
