from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import time

from mdp_cli.blueprint import Blueprint


@dataclass
class RolloutResult:
    operation_id: str
    provider_id: str
    status: str


class EasProvider:
    name = "eas"

    def build_image(self, blueprint_dir: Path, bp: Blueprint) -> str:
        seed = f"{bp.name}:{bp.build.dockerfile}:{time.time_ns()}".encode("utf-8")
        digest = sha256(seed).hexdigest()
        return f"registry.local/{bp.name}@sha256:{digest}"

    def rollout(self, bp: Blueprint, image: str, env: str) -> RolloutResult:
        op = sha256(f"{bp.name}:{image}:{env}".encode("utf-8")).hexdigest()[:12]
        return RolloutResult(operation_id=f"op-{op}", provider_id=f"eas-{bp.name}", status="running")

    def rollback(self, bp: Blueprint, to: str) -> RolloutResult:
        op = sha256(f"{bp.name}:rollback:{to}".encode("utf-8")).hexdigest()[:12]
        return RolloutResult(operation_id=f"op-{op}", provider_id=f"eas-{bp.name}", status="running")

    def status(self, bp: Blueprint) -> dict:
        return {"deployment": bp.name, "status": "running", "provider": self.name}

    def logs(self, bp: Blueprint, tail: int) -> list[str]:
        return [f"[{bp.name}] log line {i+1}" for i in range(min(tail, 20))]

    def cost(self, bp: Blueprint, group_by: str) -> dict:
        return {"deployment": bp.name, "group_by": group_by, "total_usd": 3.14}


def get_provider(name: str):
    if name != "eas":
        raise ValueError(f"unsupported provider: {name}")
    return EasProvider()
