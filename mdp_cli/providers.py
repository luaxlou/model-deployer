from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import socket
import subprocess
import tempfile
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


def _safe_name(v: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_.-]", "-", v)
    return s.strip("-").lower() or "model"


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
        tag = f"mdp-{_safe_name(bp.name)}:{int(time.time())}"
        context_dir = (blueprint_dir / bp.build.context).resolve()
        dockerfile = (blueprint_dir / bp.build.dockerfile).resolve()

        _run([
            "docker",
            "build",
            "-t",
            tag,
            "-f",
            str(dockerfile),
            str(context_dir),
        ])
        return tag

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

        if cfg.start_command:
            run_cmd.extend(["sh", "-lc", cfg.start_command])

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
        # For PAI, either use fixed image or build+push to configured image_repo.
        pai = bp.deploy.pai
        if pai.image:
            return pai.image
        if not pai.image_repo:
            raise RuntimeError("pai.image or pai.image_repo is required")

        local_tag = f"mdp-{_safe_name(bp.name)}:{int(time.time())}"
        context_dir = (blueprint_dir / bp.build.context).resolve()
        dockerfile = (blueprint_dir / bp.build.dockerfile).resolve()
        remote_tag = f"{pai.image_repo}:{int(time.time())}"

        _run(["docker", "build", "-t", local_tag, "-f", str(dockerfile), str(context_dir)])
        _run(["docker", "tag", local_tag, remote_tag])
        _run(["docker", "push", remote_tag])
        return remote_tag

    def rollout(self, blueprint_dir: Path, bp: Blueprint, image: str, env: str) -> RolloutResult:
        _ = env
        self._ensure_cli()
        params = self._params(bp, image=image)
        pai = bp.deploy.pai
        service_cfg_path = (blueprint_dir / pai.service_config).resolve()
        try:
            cfg = json.loads(service_cfg_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise RuntimeError(f"pai.service_config file not found: {service_cfg_path}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"pai.service_config is not valid JSON: {service_cfg_path}") from exc

        if isinstance(cfg, dict):
            cfg["image"] = image

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(cfg, tmp, ensure_ascii=False)
            tmp.flush()
            body_file = tmp.name

        try:
            cmd = [
                "aliyun",
                "pai",
                "UpdateService",
                "--RegionId",
                pai.region,
                "--WorkspaceId",
                pai.workspace_id,
                "--ServiceName",
                params["service_name"],
                "--Body",
                f"file://{body_file}",
            ]
            _run(cmd)
        finally:
            Path(body_file).unlink(missing_ok=True)
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
