from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
from urllib.parse import urlparse
import zipfile

import requests

from mdp_cli.blueprint import load_blueprint, validate_blueprint_dir
from mdp_cli.providers import get_provider


def _last_build_state_path(blueprint_dir: Path) -> Path:
    return blueprint_dir / ".mdp" / "last-build.json"


def _write_last_build_state(blueprint_dir: Path, provider: str, image: str) -> None:
    path = _last_build_state_path(blueprint_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider": provider,
        "image": image,
        "created_at": int(time.time()),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_last_build_image(blueprint_dir: Path, provider: str) -> str:
    path = _last_build_state_path(blueprint_dir)
    if not path.exists():
        raise RuntimeError("no last build found; run `mdp build` first or pass --image")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid last build state file: {path}") from exc

    image = str(data.get("image", "")).strip()
    if not image:
        raise RuntimeError(f"invalid last build state file: missing image in {path}")

    state_provider = str(data.get("provider", "")).strip()
    if state_provider and state_provider != provider:
        raise RuntimeError(
            f"last build provider mismatch: state={state_provider}, requested={provider}; pass --image or rebuild"
        )

    return image


def lint(blueprint_dir: Path) -> tuple[bool, list[str]]:
    errs = validate_blueprint_dir(blueprint_dir)
    return (len(errs) == 0, errs)


def _weight_target_path(blueprint_dir: Path, url: str) -> Path:
    parsed = urlparse(url)
    basename = Path(parsed.path).name or "weight.bin"
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return blueprint_dir / ".mdp" / "weights" / f"{key}-{basename}"


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(f"{target.name}.part")
    resume_from = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={resume_from}-"} if resume_from > 0 else {}

    with requests.get(url, stream=True, timeout=30, headers=headers) as resp:
        resp.raise_for_status()

        status_code = int(getattr(resp, "status_code", 200))
        accept_resume = resume_from > 0 and status_code == 206
        if resume_from > 0 and not accept_resume:
            # Server ignored/doesn't support Range; restart from scratch.
            resume_from = 0

        mode = "ab" if accept_resume else "wb"
        total_bytes = None
        resp_headers = getattr(resp, "headers", {}) or {}
        raw_total = str(resp_headers.get("Content-Length", "")).strip()
        if raw_total and raw_total.isdigit():
            content_bytes = int(raw_total)
            total_bytes = resume_from + content_bytes if accept_resume else content_bytes

        start_msg = f"[mdp] downloading weights: {url}"
        if accept_resume and resume_from > 0:
            start_msg += f" (resume from {resume_from} bytes)"
        print(start_msg, file=sys.stderr, flush=True)

        downloaded = resume_from
        last_reported_percent = -1
        with part.open(mode) as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)

                if total_bytes and total_bytes > 0:
                    percent = int(downloaded * 100 / total_bytes)
                    if percent >= last_reported_percent + 10 or percent == 100:
                        print(
                            f"[mdp] downloading weights: {percent}% ({downloaded}/{total_bytes} bytes)",
                            file=sys.stderr,
                            flush=True,
                        )
                        last_reported_percent = percent

        if not total_bytes:
            print(f"[mdp] downloading weights: {downloaded} bytes", file=sys.stderr, flush=True)
        part.replace(target)


def _is_archive(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".zip") or name.endswith(".tar") or name.endswith(".tar.gz") or name.endswith(".tgz")


def _extract_archive(archive_path: Path, output_dir: Path) -> None:
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(output_dir)
        return

    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path) as tf:
            tf.extractall(output_dir)
        return

    raise ValueError(f"unsupported archive format: {archive_path}")


def _prefetch_weights(blueprint_dir: Path) -> None:
    bp = load_blueprint(blueprint_dir)
    out_dir = blueprint_dir / ".mdp" / "weights"
    out_dir.mkdir(parents=True, exist_ok=True)
    for url in bp.build.weights:
        target = _weight_target_path(blueprint_dir, url)
        if not target.exists():
            _download_file(url, target)
        if _is_archive(target):
            _extract_archive(target, out_dir)


def build(blueprint_dir: Path, provider: str) -> str:
    _prefetch_weights(blueprint_dir)
    bp = load_blueprint(blueprint_dir)
    p = get_provider(provider)
    image = p.build_image(blueprint_dir, bp)
    _write_last_build_state(blueprint_dir, provider=provider, image=image)
    return image


def push(blueprint_dir: Path, provider: str, image: str | None = None) -> str:
    bp = load_blueprint(blueprint_dir)
    p = get_provider(provider)
    resolved_image = image or _read_last_build_image(blueprint_dir, provider=provider)
    pushed_image = p.push_image(blueprint_dir, bp, image=resolved_image)
    _write_last_build_state(blueprint_dir, provider=provider, image=pushed_image)
    return pushed_image


def deploy(blueprint_dir: Path, provider: str, image: str | None, env: str):
    bp = load_blueprint(blueprint_dir)
    p = get_provider(provider)
    resolved_image = image or _read_last_build_image(blueprint_dir, provider=provider)
    return p.rollout(blueprint_dir, bp, image=resolved_image, env=env)


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


def release(blueprint_dir: Path, provider: str, env: str) -> dict:
    try:
        image = build(blueprint_dir, provider=provider)
    except Exception as exc:
        return {"ok": False, "stage": "build", "message": str(exc)}

    try:
        image = push(blueprint_dir, provider=provider, image=image)
    except Exception as exc:
        return {"ok": False, "stage": "push", "message": str(exc)}

    try:
        rollout_res = deploy(blueprint_dir, provider=provider, image=image, env=env)
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
