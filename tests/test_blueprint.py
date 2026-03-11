from pathlib import Path

from mdp_cli.blueprint import load_blueprint, validate_blueprint_dir


def test_load_blueprint_defaults():
    bp = load_blueprint(Path("blueprints/example"))
    assert bp.deploy.health_path == "/healthz"
    assert bp.deploy.health_port == 8080
    assert bp.verify.timeout_sec == 5


def test_validate_blueprint_dir_success():
    errs = validate_blueprint_dir(Path("blueprints/example"))
    assert errs == []
