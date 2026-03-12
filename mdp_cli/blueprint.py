from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class BuildConfig:
    context: str = "."
    dockerfile: str = "Dockerfile"
    weights: list[str] = field(default_factory=list)


@dataclass
class LocalDeployConfig:
    health_path: str = "/healthz"
    health_port: int = 8080


@dataclass
class PaiDeployConfig:
    region: str = ""
    workspace_id: str = ""
    service_name: str = ""
    endpoint: str = ""
    image: str = ""
    eas_config: str = ""
    instance_type: str = ""
    replicas: int = 1


@dataclass
class DeployConfig:
    default: str = ""
    local: LocalDeployConfig = field(default_factory=LocalDeployConfig)
    eas: LocalDeployConfig = field(default_factory=LocalDeployConfig)
    pai: PaiDeployConfig = field(default_factory=PaiDeployConfig)
    configured_providers: list[str] = field(default_factory=list)


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


def load_blueprint(blueprint_dir: Path) -> Blueprint:
    raw = yaml.safe_load((blueprint_dir / "blueprint.yaml").read_text(encoding="utf-8")) or {}

    build_raw = raw.get("build") or {}
    weights_raw = build_raw.get("weights") or []
    weights: list[str] = []
    if isinstance(weights_raw, list):
        for item in weights_raw:
            if isinstance(item, str):
                weights.append(item.strip())
            elif isinstance(item, dict) and isinstance(item.get("url"), str):
                # Defensive parse for mixed/legacy shapes; validation enforces strict string[]
                weights.append(str(item.get("url", "")).strip())
    build_allowed_keys = {"context", "dockerfile"}
    build = BuildConfig(
        **{k: v for k, v in build_raw.items() if k in build_allowed_keys},
        weights=weights,
    )
    deploy_raw = raw.get("deploy") or {}
    local_raw = None
    eas_raw = None
    pai_raw = None

    providers_raw = deploy_raw.get("providers")
    if isinstance(providers_raw, list):
        for item in providers_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip().lower()
            payload = {k: v for k, v in item.items() if k != "name"}
            if name == "local":
                local_raw = payload
            elif name == "eas":
                eas_raw = payload
            elif name == "pai":
                pai_raw = payload
    else:
        legacy_local_raw = {
            "health_path": deploy_raw.get("health_path"),
            "health_port": deploy_raw.get("health_port"),
        }
        legacy_local_raw = {k: v for k, v in legacy_local_raw.items() if v is not None}
        local_raw = deploy_raw.get("local")
        if local_raw is None and legacy_local_raw:
            local_raw = legacy_local_raw
        eas_raw = deploy_raw.get("eas")
        pai_raw = deploy_raw.get("pai")
        if pai_raw is None and isinstance(raw.get("pai"), dict):
            pai_raw = raw.get("pai")

    configured: list[str] = []
    if local_raw is not None:
        configured.append("local")
    if eas_raw is not None:
        configured.append("eas")
    if pai_raw is not None:
        configured.append("pai")

    legacy_provider = str(raw.get("provider", "")).strip()
    default_provider = str(deploy_raw.get("default", legacy_provider)).strip()
    if not configured and legacy_provider in ("local", "eas", "pai"):
        configured.append(legacy_provider)

    local_allowed_keys = {"health_path", "health_port"}

    deploy = DeployConfig(
        default=default_provider,
        local=LocalDeployConfig(**{k: v for k, v in (local_raw or {}).items() if k in local_allowed_keys}),
        eas=LocalDeployConfig(**{k: v for k, v in (eas_raw or {}).items() if k in local_allowed_keys}),
        pai=PaiDeployConfig(**(pai_raw or {})),
        configured_providers=configured,
    )
    verify = VerifyConfig(**(raw.get("verify") or {}))

    return Blueprint(
        name=str(raw.get("name", "")),
        provider=legacy_provider or "local",
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
    build_raw = raw.get("build") or {}
    if isinstance(raw, dict) and "pai" in raw:
        errs.append("top-level 'pai' is not allowed; use deploy.providers with name='pai'")
    if "requirements" in build_raw:
        errs.append("build.requirements is removed; define dependencies in Dockerfile")
    if "service" in build_raw:
        errs.append("build.service is removed; define runtime entrypoint in Dockerfile")
    model_raw = build_raw.get("model") if isinstance(build_raw.get("model"), dict) else None
    if isinstance(model_raw, dict) and "code" in model_raw:
        errs.append("build.model.code is removed; package model code through Dockerfile build context")
    if isinstance(model_raw, dict) and "weights" in model_raw:
        errs.append("build.model.weights is removed; use build.weights (string array of URLs)")
    deploy_raw = raw.get("deploy") or {}
    providers_raw = deploy_raw.get("providers")
    if providers_raw is not None:
        if not isinstance(providers_raw, list):
            errs.append("deploy.providers must be an array")
        else:
            for idx, item in enumerate(providers_raw):
                if not isinstance(item, dict):
                    errs.append(f"deploy.providers[{idx}] must be an object")
                    continue
                name = str(item.get("name", "")).strip().lower()
                if name not in ("local", "eas", "pai"):
                    errs.append(f"deploy.providers[{idx}].name must be one of: local, eas, pai")
                if "start_command" in item:
                    errs.append("deploy.providers[].start_command is removed; use image ENTRYPOINT/CMD")

    bp = load_blueprint(blueprint_dir)

    if not bp.name:
        errs.append("blueprint.name is required")

    if bp.provider and bp.provider not in ("local", "eas", "pai"):
        errs.append("provider must be one of: local, eas, pai")

    configured = bp.deploy.configured_providers
    if not configured:
        errs.append("deploy must configure at least one provider in deploy.providers")
    if bp.deploy.default and bp.deploy.default not in configured:
        errs.append("deploy.default must be one of configured deploy providers")

    weights_raw = build_raw.get("weights")
    if weights_raw is None:
        errs.append("build.weights must contain at least one item")
    elif not isinstance(weights_raw, list):
        errs.append("build.weights must be an array of URL strings")
    else:
        if len(weights_raw) == 0:
            errs.append("build.weights must contain at least one item")
        for idx, w in enumerate(weights_raw):
            if not isinstance(w, str):
                errs.append(f"build.weights[{idx}] must be a URL string")
                continue
            url = w.strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                errs.append(f"build.weights[{idx}] must be http/https")

    dockerfile = blueprint_dir / bp.build.dockerfile

    if not dockerfile.exists():
        errs.append(f"missing Dockerfile: {dockerfile}")

    if "pai" in configured:
        pai = bp.deploy.pai
        if not pai.region:
            errs.append("deploy.pai.region is required when deploy.pai is configured")
        if not pai.workspace_id:
            errs.append("deploy.pai.workspace_id is required when deploy.pai is configured")
        if not pai.service_name:
            errs.append("deploy.pai.service_name is required when deploy.pai is configured")
        if not pai.image:
            errs.append("deploy.pai.image is required when deploy.pai is configured")
        if not pai.eas_config:
            errs.append("deploy.pai.eas_config is required when deploy.pai is configured")
        else:
            eas_config = blueprint_dir / pai.eas_config
            if not eas_config.exists():
                errs.append(f"missing eas config file: {eas_config}")

    if bp.verify.script:
        verify_script = blueprint_dir / bp.verify.script
        if not verify_script.exists():
            errs.append(f"missing verify script file: {verify_script}")

    return errs
