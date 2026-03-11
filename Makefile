.PHONY: install test lint plan build deploy smoke

install:
	python3 -m pip install -e .

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q

lint:
	python3 -m mdp_cli.main lint -d ./blueprints/example

plan:
	python3 -m mdp_cli.main plan -d ./blueprints/example

build:
	python3 -m mdp_cli.main build -d ./blueprints/example

deploy:
	python3 -m mdp_cli.main deploy -d ./blueprints/example

smoke:
	bash ./scripts/smoke_cli.sh
