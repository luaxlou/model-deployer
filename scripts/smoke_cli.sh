#!/usr/bin/env bash
set -euo pipefail

python3 -m mdp_cli.main lint -d ./blueprints/example
python3 -m mdp_cli.main plan -d ./blueprints/example
IMAGE=$(python3 -m mdp_cli.main build -d ./blueprints/example | python3 -c 'import json,sys; print(json.load(sys.stdin)["image"])')
python3 -m mdp_cli.main rollout -d ./blueprints/example --image "$IMAGE"
python3 -m mdp_cli.main status -d ./blueprints/example
python3 -m mdp_cli.main logs -d ./blueprints/example --tail 3
python3 -m mdp_cli.main cost -d ./blueprints/example --group-by deployment
