from pathlib import Path
import zipfile

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


def test_prefetch_weights_extracts_archive_with_top_level_dir(tmp_path, monkeypatch):
    bp_dir = tmp_path / "bp"
    bp_dir.mkdir()
    (bp_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (bp_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (bp_dir / "service.py").write_text("print('ok')\n", encoding="utf-8")
    (bp_dir / "blueprint.yaml").write_text(
        """
name: weight-archive
provider: local
build:
  weights:
    - https://example.com/tiny.zip
deploy:
  providers:
    - name: local
""".strip()
        + "\n",
        encoding="utf-8",
    )

    archive_bytes = None
    zip_path = tmp_path / "tiny.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("tiny_model/model.bin", b"abc123")
    archive_bytes = zip_path.read_bytes()

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024 * 1024):
            _ = chunk_size
            yield archive_bytes

    monkeypatch.setattr(pipeline.requests, "get", lambda *args, **kwargs: FakeResp())
    pipeline._prefetch_weights(bp_dir)

    extracted = bp_dir / ".mdp" / "weights" / "tiny_model" / "model.bin"
    assert extracted.exists()
    assert extracted.read_bytes() == b"abc123"


def test_download_file_resumes_from_part_file(tmp_path, monkeypatch):
    target = tmp_path / "model.bin"
    part = tmp_path / "model.bin.part"
    part.write_bytes(b"abc")

    calls = []

    class FakeResp:
        status_code = 206
        headers = {"Content-Length": "3", "Content-Range": "bytes 3-5/6"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024 * 1024):
            _ = chunk_size
            yield b"def"

    def fake_get(url, stream, timeout, headers=None):
        calls.append({"url": url, "stream": stream, "timeout": timeout, "headers": headers or {}})
        return FakeResp()

    monkeypatch.setattr(pipeline.requests, "get", fake_get)
    pipeline._download_file("https://example.com/model.bin", target)

    assert target.read_bytes() == b"abcdef"
    assert not part.exists()
    assert calls[0]["headers"]["Range"] == "bytes=3-"


def test_download_file_falls_back_when_server_ignores_range(tmp_path, monkeypatch):
    target = tmp_path / "model.bin"
    part = tmp_path / "model.bin.part"
    part.write_bytes(b"stale")

    class FakeResp:
        status_code = 200
        headers = {"Content-Length": "3"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024 * 1024):
            _ = chunk_size
            yield b"new"

    monkeypatch.setattr(pipeline.requests, "get", lambda *args, **kwargs: FakeResp())
    pipeline._download_file("https://example.com/model.bin", target)

    assert target.read_bytes() == b"new"
    assert not part.exists()


def test_download_file_prints_progress(tmp_path, monkeypatch, capsys):
    target = tmp_path / "model.bin"

    class FakeResp:
        status_code = 200
        headers = {"Content-Length": str(2 * 1024 * 1024)}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024 * 1024):
            _ = chunk_size
            yield b"a" * (1024 * 1024)
            yield b"b" * (1024 * 1024)

    monkeypatch.setattr(pipeline.requests, "get", lambda *args, **kwargs: FakeResp())
    pipeline._download_file("https://example.com/model.bin", target)
    captured = capsys.readouterr()

    assert "downloading" in captured.err
    assert "100%" in captured.err


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
