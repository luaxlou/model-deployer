from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import socket
import subprocess
import sys
import time

from mdp_cli.blueprint import Blueprint


@dataclass
class RolloutResult:
    status: str
    endpoint: str
    container_name: str


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"command failed: {' '.join(cmd)}; {detail}")
    return proc.stdout.strip()


def _run_with_heartbeat(cmd: list[str], step: str, interval_sec: int = 5) -> str:
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    started = time.time()
    while True:
        try:
            out, err = proc.communicate(timeout=interval_sec)
            break
        except subprocess.TimeoutExpired:
            elapsed = int(time.time() - started)
            print(f"[mdp] {step} running... {elapsed}s", file=sys.stderr, flush=True)

    if proc.returncode != 0:
        detail = (err or out or "").strip()
        raise RuntimeError(f"command failed: {' '.join(cmd)}; {detail}")
    return (out or "").strip()


def _run_stream(cmd: list[str], step: str) -> None:
    print(f"[mdp] {step}: {' '.join(cmd)}", file=sys.stderr, flush=True)
    proc = subprocess.Popen(cmd)
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"command failed ({code}): {' '.join(cmd)}")


def _safe_name(v: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_.-]", "-", v)
    return s.strip("-").lower() or "model"


def _split_image_ref(image: str) -> tuple[str, str]:
    image = image.strip()
    if "@" in image:
        base, digest = image.split("@", 1)
        return base, "@" + digest
    last_slash = image.rfind("/")
    last_colon = image.rfind(":")
    if last_colon > last_slash:
        return image[:last_colon], image[last_colon:]
    return image, ""


def _release_tag() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short=8", "HEAD"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        tag = (proc.stdout or "").strip()
        if tag:
            return tag
    return str(int(time.time()))


def _find_host_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if s.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class LocalProvider:
    name = "local"

    def build_image(self, blueprint_dir: Path, bp: Blueprint) -> str:
        tag = f"mdp-{_safe_name(bp.name)}:{_release_tag()}"
        context_dir = (blueprint_dir / bp.build.context).resolve()
        dockerfile = (blueprint_dir / bp.build.dockerfile).resolve()

        _run_stream([
            "docker",
            "build",
            "-t",
            tag,
            "-f",
            str(dockerfile),
            str(context_dir),
        ], step="docker build")
        return tag

    def push_image(self, blueprint_dir: Path, bp: Blueprint, image: str) -> str:
        _ = blueprint_dir
        _ = bp
        return image

    def rollout(self, blueprint_dir: Path, bp: Blueprint, image: str, env: str) -> RolloutResult:
        _ = blueprint_dir
        cfg = bp.deploy.local if self.name == "local" else bp.deploy.eas
        container_name = _safe_name(f"{bp.name}-{env}")
        host_port = _find_host_port(cfg.health_port)

        # Best effort: remove previous container with same name.
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, text=True)

        run_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{host_port}:{cfg.health_port}",
            image,
        ]

        _run(run_cmd)
        endpoint = f"http://127.0.0.1:{host_port}"
        return RolloutResult(
            status="running",
            endpoint=endpoint,
            container_name=container_name,
        )

    def status(self, bp: Blueprint) -> dict:
        name = _safe_name(f"{bp.name}-prod")
        out = _run(["docker", "inspect", name])
        data = json.loads(out)[0]
        state = data.get("State", {})
        return {
            "deployment": bp.name,
            "provider": self.name,
            "container": name,
            "status": state.get("Status", "unknown"),
        }

    def logs(self, bp: Blueprint, tail: int) -> list[str]:
        name = _safe_name(f"{bp.name}-prod")
        out = _run(["docker", "logs", "--tail", str(tail), name])
        return out.splitlines()

    def cost(self, bp: Blueprint, group_by: str) -> dict:
        # Local mode has no external billable metrics.
        return {"deployment": bp.name, "group_by": group_by, "total_usd": 0.0}


# Keep eas alias for compatibility; current behavior is local Docker execution.
class EasProvider(LocalProvider):
    name = "eas"


class PaiProvider:
    name = "pai"

    def _ensure_cli(self) -> None:
        proc = subprocess.run(["aliyun", "--version"], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("aliyun CLI is required for provider=pai")

    def _params(self, bp: Blueprint, image: str = "") -> dict[str, str]:
        pai = bp.deploy.pai
        return {
            "name": bp.name,
            "service_name": pai.service_name or bp.name,
            "image": image,
            "region": pai.region,
            "workspace_id": pai.workspace_id,
            "instance_type": pai.instance_type,
            "replicas": str(pai.replicas),
            "endpoint": pai.endpoint,
        }

    def build_image(self, blueprint_dir: Path, bp: Blueprint) -> str:
        release_tag = _release_tag()
        local_tag = f"mdp-{_safe_name(bp.name)}:{release_tag}"
        context_dir = (blueprint_dir / bp.build.context).resolve()
        dockerfile = (blueprint_dir / bp.build.dockerfile).resolve()
        _run_stream(["docker", "build", "-t", local_tag, "-f", str(dockerfile), str(context_dir)], step="docker build")
        return local_tag

    def push_image(self, blueprint_dir: Path, bp: Blueprint, image: str) -> str:
        _ = blueprint_dir
        pai = bp.deploy.pai
        push_repo = pai.image
        if not push_repo:
            raise RuntimeError("deploy.pai.image is required")

        push_repo_base, _ = _split_image_ref(push_repo)
        _, suffix = _split_image_ref(image)
        if not suffix:
            raise RuntimeError(f"built image has no tag/digest: {image}")
        push_tag = f"{push_repo_base}{suffix}"
        _run(["docker", "tag", image, push_tag])
        _run_stream(["docker", "push", push_tag], step="docker push")
        return push_tag

    def rollout(self, blueprint_dir: Path, bp: Blueprint, image: str, env: str) -> RolloutResult:
        _ = env
        self._ensure_cli()
        params = self._params(bp, image=image)
        pai = bp.deploy.pai
        service_cfg_path = (blueprint_dir / pai.eas_config).resolve()
        try:
            cfg = json.loads(service_cfg_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(f"deploy.pai.eas_config file not found: {service_cfg_path}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"deploy.pai.eas_config is not valid JSON: {service_cfg_path}") from exc

        if isinstance(cfg, dict):
            target_image = ""
            container_image_path = False
            containers = cfg.get("containers")
            if (
                isinstance(containers, list)
                and len(containers) > 0
                and isinstance(containers[0], dict)
                and isinstance(containers[0].get("image"), str)
            ):
                target_image = containers[0]["image"].strip()
                container_image_path = True
            elif isinstance(cfg.get("image"), str):
                target_image = str(cfg.get("image", "")).strip()

            if not target_image:
                raise RuntimeError(
                    "eas config JSON must set private pull image in containers[0].image (preferred) or image"
                )

            private_repo, _ = _split_image_ref(target_image)
            _, built_suffix = _split_image_ref(image)
            if built_suffix:
                new_private_image = f"{private_repo}{built_suffix}"
            else:
                new_private_image = target_image

            if container_image_path:
                containers[0]["image"] = new_private_image
            else:
                cfg["image"] = new_private_image

        cmd = [
            "aliyun",
            "eas",
            "UpdateService",
            "--region",
            pai.region,
            "--ClusterId",
            pai.region,
            "--ServiceName",
            params["service_name"],
            "--body",
            json.dumps(cfg, ensure_ascii=False),
        ]
        _run_with_heartbeat(cmd, step="pai update service")
        endpoint = pai.endpoint
        if not endpoint:
            raise RuntimeError("pai.endpoint is required for verify after rollout")
        return RolloutResult(status="running", endpoint=endpoint, container_name=params["service_name"])

    def status(self, bp: Blueprint) -> dict:
        self._ensure_cli()
        params = self._params(bp, image=bp.deploy.pai.image)
        cmd = [
            "aliyun",
            "pai",
            "GetService",
            "--RegionId",
            params["region"],
            "--WorkspaceId",
            params["workspace_id"],
            "--ServiceName",
            params["service_name"],
        ]
        out = _run(cmd)
        return {"deployment": bp.name, "provider": self.name, "status_raw": out}

    def logs(self, bp: Blueprint, tail: int) -> list[str]:
        self._ensure_cli()
        params = self._params(bp, image=bp.deploy.pai.image)
        cmd = [
            "aliyun",
            "pai",
            "ListServiceLogs",
            "--RegionId",
            params["region"],
            "--WorkspaceId",
            params["workspace_id"],
            "--ServiceName",
            params["service_name"],
            "--PageSize",
            str(tail),
        ]
        out = _run(cmd)
        return out.splitlines()

    def cost(self, bp: Blueprint, group_by: str) -> dict:
        self._ensure_cli()
        params = self._params(bp, image=bp.deploy.pai.image)
        cmd = [
            "aliyun",
            "pai",
            "QueryServiceCost",
            "--RegionId",
            params["region"],
            "--WorkspaceId",
            params["workspace_id"],
            "--ServiceName",
            params["service_name"],
            "--GroupBy",
            group_by,
        ]
        out = _run(cmd)
        return {"deployment": bp.name, "group_by": group_by, "cost_raw": out}


def get_provider(name: str):
    if name == "local":
        return LocalProvider()
    if name == "eas":
        return EasProvider()
    if name == "pai":
        return PaiProvider()
    raise ValueError(f"unsupported provider: {name}")
