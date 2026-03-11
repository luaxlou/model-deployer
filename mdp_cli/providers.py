from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import re
import socket
import subprocess
import time

from mdp_cli.blueprint import Blueprint


@dataclass
class RolloutResult:
    operation_id: str
    provider_id: str
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

    def rollout(self, bp: Blueprint, image: str, env: str) -> RolloutResult:
        container_name = _safe_name(f"{bp.name}-{env}")
        host_port = _find_host_port(bp.deploy.health_port)

        # Best effort: remove previous container with same name.
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, text=True)

        run_cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{host_port}:{bp.deploy.health_port}",
            image,
        ]

        if bp.deploy.start_command:
            run_cmd.extend(["sh", "-lc", bp.deploy.start_command])

        cid = _run(run_cmd)
        op = sha256(f"{bp.name}:{cid}:{env}".encode("utf-8")).hexdigest()[:12]
        endpoint = f"http://127.0.0.1:{host_port}"
        return RolloutResult(
            operation_id=f"op-{op}",
            provider_id=container_name,
            status="running",
            endpoint=endpoint,
            container_name=container_name,
        )

    def rollback(self, bp: Blueprint, to: str) -> RolloutResult:
        # Stateless mode: explicit target image is required for real rollback.
        if to in ("", "previous"):
            raise RuntimeError("local rollback requires explicit --to <image>")
        return self.rollout(bp, image=to, env="rollback")

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


def get_provider(name: str):
    if name == "local":
        return LocalProvider()
    if name == "eas":
        return EasProvider()
    raise ValueError(f"unsupported provider: {name}")
