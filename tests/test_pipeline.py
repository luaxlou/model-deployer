from pathlib import Path

from mdp_cli import pipeline
from mdp_cli.blueprint import Blueprint, BuildConfig, DeployConfig, LocalDeployConfig
from mdp_cli.providers import LocalProvider


def test_deploy_build_only_skips_rollout_and_verify(monkeypatch):
    calls = []

    def fake_build(_dir: Path, provider: str):
        assert provider == "local"
        calls.append("build")
        return "example:tag"

    def fake_rollout(*args, **kwargs):
        calls.append("rollout")
        raise AssertionError("rollout should not be called in build-only mode")

    def fake_verify(*args, **kwargs):
        calls.append("verify")
        raise AssertionError("verify should not be called in build-only mode")

    monkeypatch.setattr(pipeline, "build", fake_build)
    monkeypatch.setattr(pipeline, "rollout", fake_rollout)
    monkeypatch.setattr(pipeline, "verify", fake_verify)

    result = pipeline.deploy(
        Path("blueprints/example"),
        provider="local",
        env="prod",
        build_only=True,
    )

    assert result == {
        "ok": True,
        "stage": "build",
        "image": "example:tag",
        "mode": "build-only",
    }
    assert calls == ["build"]


def test_prefetch_weights_downloads_file(tmp_path, monkeypatch):
    bp_dir = tmp_path / "bp"
    bp_dir.mkdir()
    (bp_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (bp_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (bp_dir / "service.py").write_text("print('ok')\n", encoding="utf-8")
    (bp_dir / "blueprint.yaml").write_text(
        """
name: weight-download
provider: local
build:
  weights:
    - https://example.com/tiny.bin
deploy:
  providers:
    - name: local
""".strip()
        + "\n",
        encoding="utf-8",
    )

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024 * 1024):
            _ = chunk_size
            yield b"abc123"

    monkeypatch.setattr(pipeline.requests, "get", lambda *args, **kwargs: FakeResp())
    pipeline._prefetch_weights(bp_dir)

    out_dir = bp_dir / ".mdp" / "weights"
    matches = list(out_dir.glob("*-tiny.bin"))
    assert len(matches) == 1
    assert matches[0].read_bytes() == b"abc123"


def test_local_rollout_uses_image_default_command(tmp_path, monkeypatch):
    provider = LocalProvider()
    bp = Blueprint(
        name="demo",
        build=BuildConfig(),
        deploy=DeployConfig(local=LocalDeployConfig(health_port=18080)),
    )

    captured = {}

    def fake_run(cmd):
        captured["cmd"] = cmd
        return "ok"

    monkeypatch.setattr("mdp_cli.providers._find_host_port", lambda _: 18081)
    monkeypatch.setattr("mdp_cli.providers._run", fake_run)
    monkeypatch.setattr(
        "mdp_cli.providers.subprocess.run",
        lambda *args, **kwargs: None,
    )

    res = provider.rollout(tmp_path, bp, image="demo:latest", env="prod")

    assert res.status == "running"
    assert captured["cmd"] == [
        "docker",
        "run",
        "-d",
        "--name",
        "demo-prod",
        "-p",
        "18081:18080",
        "demo:latest",
    ]
