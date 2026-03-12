from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class WeightAsset:
    name: str
    url: str
    sha256: str | None = None


@dataclass
class ModelConfig:
    code: str | None = None
    weights: list[WeightAsset] = field(default_factory=list)


@dataclass
class BuildConfig:
    context: str = "."
    dockerfile: str = "Dockerfile"
    requirements: str = "requirements.txt"
    service: str = "service.py"
    model: ModelConfig = field(default_factory=ModelConfig)


@dataclass
class PaiConfig:
    region: str = ""
    workspace_id: str = ""
    service_name: str = ""
    endpoint: str = ""
    image: str = ""
    image_repo: str = ""
    service_config: str = ""
    instance_type: str = ""
    replicas: int = 1
    status_cmd: str = ""
    logs_cmd: str = ""
    cost_cmd: str = ""


@dataclass
class DeployConfig:
    health_path: str = "/healthz"
    health_port: int = 8080
    start_command: str = "python service.py"
    pai: PaiConfig = field(default_factory=PaiConfig)


@dataclass
class VerifyConfig:
    timeout_sec: int = 300
    interval_sec: int = 5
    script: str = ""


@dataclass
class Blueprint:
    name: str
    provider: str = "local"
    build: BuildConfig = field(default_factory=BuildConfig)
    deploy: DeployConfig = field(default_factory=DeployConfig)
    verify: VerifyConfig = field(default_factory=VerifyConfig)


def _as_weight(item: dict[str, Any]) -> WeightAsset:
    return WeightAsset(
        name=str(item.get("name", "")),
        url=str(item.get("url", "")),
        sha256=item.get("sha256"),
    )


def load_blueprint(blueprint_dir: Path) -> Blueprint:
    raw = yaml.safe_load((blueprint_dir / "blueprint.yaml").read_text(encoding="utf-8")) or {}

    build_raw = raw.get("build") or {}
    model_raw = (build_raw.get("model") or raw.get("model") or {})
    weights = [_as_weight(w) for w in (model_raw.get("weights") or [])]
    model = ModelConfig(code=model_raw.get("code"), weights=weights)
    build = BuildConfig(**{k: v for k, v in build_raw.items() if k != "model"}, model=model)
    deploy_raw = raw.get("deploy") or {}
    pai_raw = deploy_raw.get("pai") or {}
    deploy = DeployConfig(**{k: v for k, v in deploy_raw.items() if k != "pai"}, pai=PaiConfig(**pai_raw))
    verify = VerifyConfig(**(raw.get("verify") or {}))

    return Blueprint(
        name=str(raw.get("name", "")),
        provider=str(raw.get("provider", "local")),
        build=build,
        deploy=deploy,
        verify=verify,
    )


def validate_blueprint_dir(blueprint_dir: Path) -> list[str]:
    errs: list[str] = []

    if not blueprint_dir.exists() or not blueprint_dir.is_dir():
        return [f"blueprint dir not found: {blueprint_dir}"]

    blueprint_path = blueprint_dir / "blueprint.yaml"
    if not blueprint_path.exists():
        return [f"missing file: {blueprint_path}"]

    raw = yaml.safe_load(blueprint_path.read_text(encoding="utf-8")) or {}
    if isinstance(raw, dict) and "pai" in raw:
        errs.append("top-level 'pai' is not allowed; use deploy.pai")

    bp = load_blueprint(blueprint_dir)

    if not bp.name:
        errs.append("blueprint.name is required")

    if bp.provider not in ("local", "eas", "pai"):
        errs.append("provider must be one of: local, eas, pai")

    if not bp.build.model.weights:
        errs.append("build.model.weights must contain at least one item")
    else:
        for idx, w in enumerate(bp.build.model.weights):
            if not w.name:
                errs.append(f"build.model.weights[{idx}].name is required")
            if not (w.url.startswith("http://") or w.url.startswith("https://")):
                errs.append(f"build.model.weights[{idx}].url must be http/https")

    dockerfile = blueprint_dir / bp.build.dockerfile
    requirements = blueprint_dir / bp.build.requirements
    service = blueprint_dir / bp.build.service

    if not dockerfile.exists():
        errs.append(f"missing Dockerfile: {dockerfile}")
    if not requirements.exists():
        errs.append(f"missing requirements file: {requirements}")
    if not service.exists():
        errs.append(f"missing service file: {service}")

    if bp.build.model.code:
        model_code = blueprint_dir / bp.build.model.code
        if not model_code.exists():
            errs.append(f"missing model code file: {model_code}")

    if bp.provider == "pai":
        pai = bp.deploy.pai
        if not pai.region:
            errs.append("deploy.pai.region is required when provider=pai")
        if not pai.workspace_id:
            errs.append("deploy.pai.workspace_id is required when provider=pai")
        if not pai.service_name:
            errs.append("deploy.pai.service_name is required when provider=pai")
        if not (pai.image or pai.image_repo):
            errs.append("deploy.pai.image or deploy.pai.image_repo is required when provider=pai")
        if not pai.service_config:
            errs.append("deploy.pai.service_config is required when provider=pai")
        else:
            service_config = blueprint_dir / pai.service_config
            if not service_config.exists():
                errs.append(f"missing pai service config file: {service_config}")
        if not pai.status_cmd:
            errs.append("deploy.pai.status_cmd is required when provider=pai")
        if not pai.logs_cmd:
            errs.append("deploy.pai.logs_cmd is required when provider=pai")

    if bp.verify.script:
        verify_script = blueprint_dir / bp.verify.script
        if not verify_script.exists():
            errs.append(f"missing verify script file: {verify_script}")

    return errs
