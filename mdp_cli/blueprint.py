from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class BuildConfig:
    context: str = "."
    dockerfile: str = "Dockerfile"
    requirements: str = "requirements.txt"
    service: str = "service.py"


@dataclass
class DeployConfig:
    health_path: str = "/healthz"
    health_port: int = 8080
    start_command: str = "python service.py"


@dataclass
class VerifyConfig:
    timeout_sec: int = 300
    interval_sec: int = 5


@dataclass
class PaiConfig:
    region: str = ""
    workspace_id: str = ""
    service_name: str = ""
    endpoint: str = ""
    image: str = ""
    image_repo: str = ""
    instance_type: str = ""
    replicas: int = 1
    deploy_cmd: str = ""
    rollback_cmd: str = ""
    status_cmd: str = ""
    logs_cmd: str = ""
    cost_cmd: str = ""


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
class Blueprint:
    name: str
    provider: str = "local"
    build: BuildConfig = field(default_factory=BuildConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    deploy: DeployConfig = field(default_factory=DeployConfig)
    verify: VerifyConfig = field(default_factory=VerifyConfig)
    pai: PaiConfig = field(default_factory=PaiConfig)


def _as_weight(item: dict[str, Any]) -> WeightAsset:
    return WeightAsset(
        name=str(item.get("name", "")),
        url=str(item.get("url", "")),
        sha256=item.get("sha256"),
    )


def load_blueprint(blueprint_dir: Path) -> Blueprint:
    raw = yaml.safe_load((blueprint_dir / "blueprint.yaml").read_text(encoding="utf-8")) or {}

    build = BuildConfig(**(raw.get("build") or {}))
    deploy = DeployConfig(**(raw.get("deploy") or {}))
    verify = VerifyConfig(**(raw.get("verify") or {}))
    pai = PaiConfig(**(raw.get("pai") or {}))

    model_raw = raw.get("model") or {}
    weights = [_as_weight(w) for w in (model_raw.get("weights") or [])]
    model = ModelConfig(code=model_raw.get("code"), weights=weights)

    return Blueprint(
        name=str(raw.get("name", "")),
        provider=str(raw.get("provider", "local")),
        build=build,
        model=model,
        deploy=deploy,
        verify=verify,
        pai=pai,
    )


def validate_blueprint_dir(blueprint_dir: Path) -> list[str]:
    errs: list[str] = []

    if not blueprint_dir.exists() or not blueprint_dir.is_dir():
        return [f"blueprint dir not found: {blueprint_dir}"]

    blueprint_path = blueprint_dir / "blueprint.yaml"
    if not blueprint_path.exists():
        return [f"missing file: {blueprint_path}"]

    bp = load_blueprint(blueprint_dir)

    if not bp.name:
        errs.append("blueprint.name is required")

    if bp.provider not in ("local", "eas", "pai"):
        errs.append("provider must be one of: local, eas, pai")

    if not bp.model.weights:
        errs.append("model.weights must contain at least one item")
    else:
        for idx, w in enumerate(bp.model.weights):
            if not w.name:
                errs.append(f"model.weights[{idx}].name is required")
            if not (w.url.startswith("http://") or w.url.startswith("https://")):
                errs.append(f"model.weights[{idx}].url must be http/https")

    dockerfile = blueprint_dir / bp.build.dockerfile
    requirements = blueprint_dir / bp.build.requirements
    service = blueprint_dir / bp.build.service

    if not dockerfile.exists():
        errs.append(f"missing Dockerfile: {dockerfile}")
    if not requirements.exists():
        errs.append(f"missing requirements file: {requirements}")
    if not service.exists():
        errs.append(f"missing service file: {service}")

    if bp.model.code:
        model_code = blueprint_dir / bp.model.code
        if not model_code.exists():
            errs.append(f"missing model code file: {model_code}")

    if bp.provider == "pai":
        if not bp.pai.region:
            errs.append("pai.region is required when provider=pai")
        if not bp.pai.workspace_id:
            errs.append("pai.workspace_id is required when provider=pai")
        if not bp.pai.service_name:
            errs.append("pai.service_name is required when provider=pai")
        if not (bp.pai.image or bp.pai.image_repo):
            errs.append("pai.image or pai.image_repo is required when provider=pai")
        if not bp.pai.deploy_cmd:
            errs.append("pai.deploy_cmd is required when provider=pai")
        if not bp.pai.status_cmd:
            errs.append("pai.status_cmd is required when provider=pai")
        if not bp.pai.logs_cmd:
            errs.append("pai.logs_cmd is required when provider=pai")

    return errs
