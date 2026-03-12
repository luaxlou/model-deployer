from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlparse

import requests

from mdp_cli.blueprint import load_blueprint, validate_blueprint_dir
from mdp_cli.providers import get_provider


def lint(blueprint_dir: Path) -> tuple[bool, list[str]]:
    errs = validate_blueprint_dir(blueprint_dir)
    return (len(errs) == 0, errs)


def _weight_target_path(blueprint_dir: Path, name: str, url: str) -> Path:
    parsed = urlparse(url)
    basename = Path(parsed.path).name or "weight.bin"
    safe_name = "".join(c if c.isalnum() or c in ("-", "_", ".") else "-" for c in name).strip("-") or "weight"
    return blueprint_dir / ".mdp" / "weights" / f"{safe_name}-{basename}"


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        with target.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def _prefetch_weights(blueprint_dir: Path) -> None:
    bp = load_blueprint(blueprint_dir)
    for w in bp.build.model.weights:
        target = _weight_target_path(blueprint_dir, w.name, w.url)
        if target.exists() and w.sha256:
            if _sha256_of_file(target) == w.sha256.lower():
                continue
            target.unlink(missing_ok=True)
        elif target.exists():
            continue

        _download_file(w.url, target)
        if w.sha256:
            actual = _sha256_of_file(target)
            if actual != w.sha256.lower():
                target.unlink(missing_ok=True)
                raise RuntimeError(
                    f"weight sha256 mismatch for {w.name}: expected {w.sha256.lower()}, got {actual}"
                )


def build(blueprint_dir: Path, provider: str) -> str:
    _prefetch_weights(blueprint_dir)
    bp = load_blueprint(blueprint_dir)
    p = get_provider(provider)
    return p.build_image(blueprint_dir, bp)


def rollout(blueprint_dir: Path, provider: str, image: str, env: str):
    bp = load_blueprint(blueprint_dir)
    p = get_provider(provider)
    return p.rollout(blueprint_dir, bp, image=image, env=env)


def verify(
    blueprint_dir: Path,
    provider: str,
    endpoint: str | None = None,
    timeout_sec: int | None = None,
    interval_sec: int | None = None,
) -> tuple[bool, str]:
    bp = load_blueprint(blueprint_dir)

    timeout = timeout_sec or bp.verify.timeout_sec
    interval = interval_sec or bp.verify.interval_sec

    if provider == "pai":
        base = endpoint or bp.deploy.pai.endpoint
        health_path = bp.deploy.local.health_path
    elif provider == "eas":
        base = endpoint or f"http://127.0.0.1:{bp.deploy.eas.health_port}"
        health_path = bp.deploy.eas.health_path
    else:
        base = endpoint or f"http://127.0.0.1:{bp.deploy.local.health_port}"
        health_path = bp.deploy.local.health_path

    if not base:
        return False, "verify endpoint is required"
    health_url = f"{base}{health_path}"

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

    if bp.verify.script:
        smoke = blueprint_dir / bp.verify.script
        env = dict(os.environ)
        env["MDP_ENDPOINT"] = base
        proc = subprocess.run(["bash", str(smoke)], capture_output=True, text=True, env=env)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            return False, f"smoke failed: {detail}"

    return True, "verification passed"


def deploy(blueprint_dir: Path, provider: str, env: str, build_only: bool = False) -> dict:
    try:
        image = build(blueprint_dir, provider=provider)
    except Exception as exc:
        return {"ok": False, "stage": "build", "message": str(exc)}
    if build_only:
        return {"ok": True, "stage": "build", "image": image, "mode": "build-only"}

    try:
        rollout_res = rollout(blueprint_dir, provider=provider, image=image, env=env)
    except Exception as exc:
        return {"ok": False, "stage": "deploy", "message": str(exc)}

    ok, msg = verify(blueprint_dir, provider=provider, endpoint=rollout_res.endpoint)
    if ok:
        return {
            "ok": True,
            "stage": "verify",
            "image": image,
            "status": rollout_res.status,
            "endpoint": rollout_res.endpoint,
            "container_name": rollout_res.container_name,
        }

    return {"ok": False, "stage": "verify", "message": msg}
