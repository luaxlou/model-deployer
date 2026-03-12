from pathlib import Path

from mdp_cli.blueprint import load_blueprint, validate_blueprint_dir


def test_load_blueprint_defaults():
    bp = load_blueprint(Path("blueprints/example"))
    assert bp.deploy.local.health_path == "/healthz"
    assert bp.deploy.local.health_port == 18080
    assert bp.verify.timeout_sec == 60


def test_validate_blueprint_dir_success():
    errs = validate_blueprint_dir(Path("blueprints/example"))
    assert errs == []


def test_validate_pai_blueprint_dir_success():
    errs = validate_blueprint_dir(Path("blueprints/pai-example"))
    assert errs == []


def test_validate_pai_blueprint_with_build_model_uses_service_config(tmp_path):
    bp_dir = tmp_path / "bp"
    bp_dir.mkdir()
    (bp_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (bp_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (bp_dir / "service.py").write_text("print('ok')\n", encoding="utf-8")
    (bp_dir / "pai-service.json").write_text("{}", encoding="utf-8")
    (bp_dir / "blueprint.yaml").write_text(
        """
name: pai-no-deploy-cmd
provider: pai
build:
  model:
    weights:
      - name: model-weights
        url: https://example.com/model.bin
deploy:
  providers:
    - name: pai
      region: cn-hangzhou
      workspace_id: "ws-1"
      service_name: demo
      image: registry.cn-hangzhou.aliyuncs.com/ns/demo:latest
      service_config: pai-service.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    errs = validate_blueprint_dir(bp_dir)
    assert errs == []


def test_validate_blueprint_verify_script_must_exist_when_specified(tmp_path):
    bp_dir = tmp_path / "bp-verify"
    bp_dir.mkdir()
    (bp_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (bp_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (bp_dir / "service.py").write_text("print('ok')\n", encoding="utf-8")
    (bp_dir / "blueprint.yaml").write_text(
        """
name: verify-script-missing
provider: local
build:
  model:
    weights:
      - name: model-weights
        url: https://example.com/model.bin
verify:
  script: smoke.sh
""".strip()
        + "\n",
        encoding="utf-8",
    )

    errs = validate_blueprint_dir(bp_dir)
    assert len(errs) == 1
    assert "missing verify script file" in errs[0]


def test_validate_blueprint_rejects_top_level_pai(tmp_path):
    bp_dir = tmp_path / "bp-top-pai"
    bp_dir.mkdir()
    (bp_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (bp_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (bp_dir / "service.py").write_text("print('ok')\n", encoding="utf-8")
    (bp_dir / "pai-service.json").write_text("{}", encoding="utf-8")
    (bp_dir / "blueprint.yaml").write_text(
        """
name: top-pai
provider: pai
build:
  model:
    weights:
      - name: model-weights
        url: https://example.com/model.bin
pai:
  region: cn-hangzhou
  workspace_id: "ws-1"
  service_name: demo
  image: registry.cn-hangzhou.aliyuncs.com/ns/demo:latest
  service_config: pai-service.json
""".strip()
        + "\n",
        encoding="utf-8",
    )

    errs = validate_blueprint_dir(bp_dir)
    assert "top-level 'pai' is not allowed; use deploy.providers with name='pai'" in errs
