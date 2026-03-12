from pathlib import Path

from mdp_cli import pipeline


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
  model:
    weights:
      - name: tiny
        url: https://example.com/tiny.bin
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

    out = bp_dir / ".mdp" / "weights" / "tiny-tiny.bin"
    assert out.exists()
    assert out.read_bytes() == b"abc123"
