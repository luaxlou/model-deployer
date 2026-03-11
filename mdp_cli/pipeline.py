from __future__ import annotations

from pathlib import Path
import subprocess
import time

import requests

from mdp_cli.blueprint import load_blueprint, validate_blueprint_dir
from mdp_cli.providers import get_provider


def lint(blueprint_dir: Path) -> tuple[bool, list[str]]:
    errs = validate_blueprint_dir(blueprint_dir)
    return (len(errs) == 0, errs)


def build(blueprint_dir: Path, provider: str) -> str:
    bp = load_blueprint(blueprint_dir)
    p = get_provider(provider)
    return p.build_image(blueprint_dir, bp)


def rollout(blueprint_dir: Path, provider: str, image: str, env: str):
    bp = load_blueprint(blueprint_dir)
    p = get_provider(provider)
    return p.rollout(bp, image=image, env=env)


def rollback(blueprint_dir: Path, provider: str, to: str):
    bp = load_blueprint(blueprint_dir)
    p = get_provider(provider)
    return p.rollback(bp, to=to)


def verify(blueprint_dir: Path, timeout_sec: int | None = None, interval_sec: int | None = None) -> tuple[bool, str]:
    bp = load_blueprint(blueprint_dir)

    timeout = timeout_sec or bp.verify.timeout_sec
    interval = interval_sec or bp.verify.interval_sec

    health_url = f"http://127.0.0.1:{bp.deploy.health_port}{bp.deploy.health_path}"

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(health_url, timeout=3)
            if 200 <= resp.status_code < 300:
                break
        except requests.RequestException:
            pass
        time.sleep(interval)
    else:
        return False, f"health check failed: {health_url}"

    smoke = blueprint_dir / "smoke.sh"
    if smoke.exists():
        proc = subprocess.run(["bash", str(smoke)], capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            return False, f"smoke failed: {detail}"

    return True, "verification passed"


def deploy(blueprint_dir: Path, provider: str, env: str, on_fail: str) -> dict:
    ok, errs = lint(blueprint_dir)
    if not ok:
        return {"ok": False, "stage": "lint", "errors": errs}

    image = build(blueprint_dir, provider)

    rollout_res = rollout(blueprint_dir, provider, image=image, env=env)

    ok, msg = verify(blueprint_dir)
    if ok:
        return {
            "ok": True,
            "stage": "done",
            "image": image,
            "operation_id": rollout_res.operation_id,
            "provider_id": rollout_res.provider_id,
        }

    if on_fail == "rollback":
        rollback_res = rollback(blueprint_dir, provider, to="previous")
        return {
            "ok": False,
            "stage": "verify",
            "message": msg,
            "rollback_operation_id": rollback_res.operation_id,
        }

    return {"ok": False, "stage": "verify", "message": msg}
