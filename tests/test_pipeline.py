from pathlib import Path
import zipfile

from mdp_cli import pipeline
from mdp_cli.blueprint import Blueprint, BuildConfig, DeployConfig, LocalDeployConfig
from mdp_cli.providers import LocalProvider


def test_release_runs_build_push_deploy_verify(monkeypatch):
    calls = []

    def fake_build(_dir: Path, provider: str):
        assert provider == "local"
        calls.append("build")
        return "example:tag"

    def fake_push(_dir: Path, provider: str, image: str | None):
        assert provider == "local"
        assert image == "example:tag"
        calls.append("push")
        return "example:tag"

    class DeployRes:
        status = "running"
        endpoint = "http://127.0.0.1:18080"
        container_name = "demo-prod"

    def fake_deploy(*args, **kwargs):
        calls.append("deploy")
        return DeployRes()

    def fake_verify(*args, **kwargs):
        calls.append("verify")
        return True, "verification passed"

    monkeypatch.setattr(pipeline, "build", fake_build)
    monkeypatch.setattr(pipeline, "push", fake_push)
    monkeypatch.setattr(pipeline, "deploy", fake_deploy)
    monkeypatch.setattr(pipeline, "verify", fake_verify)

    result = pipeline.release(
        Path("blueprints/example"),
        provider="local",
        env="prod",
    )

    assert result["ok"] is True
    assert result["stage"] == "verify"
    assert result["image"] == "example:tag"
    assert calls == ["build", "push", "deploy", "verify"]


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


def test_prefetch_weights_downloads_hf_repo_files(tmp_path, monkeypatch):
    bp_dir = tmp_path / "bp"
    bp_dir.mkdir()
    (bp_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (bp_dir / "blueprint.yaml").write_text(
        """
name: weight-hf-repo
provider: local
build:
  weights:
    - https://huggingface.co/ZhengPeng7/BiRefNet_dynamic
deploy:
  providers:
    - name: local
""".strip()
        + "\n",
        encoding="utf-8",
    )

    downloaded = []

    def fake_list_repo_files(repo_id, repo_type, revision=None, token=None):
        assert repo_id == "ZhengPeng7/BiRefNet_dynamic"
        assert repo_type == "model"
        assert revision is None
        assert token is None
        return ["config.json", "model.safetensors", "subdir/tokenizer.json"]

    def fake_hf_hub_download(
        repo_id,
        filename,
        repo_type,
        revision,
        local_dir,
        local_dir_use_symlinks,
        token=None,
    ):
        assert token is None
        downloaded.append((repo_id, filename, repo_type, revision, Path(local_dir), local_dir_use_symlinks))
        path = Path(local_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
        return str(path)

    monkeypatch.setattr(pipeline, "list_repo_files", fake_list_repo_files, raising=False)
    monkeypatch.setattr(pipeline, "hf_hub_download", fake_hf_hub_download, raising=False)
    monkeypatch.setattr(
        pipeline.requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("requests.get should not be used for HF repo")),
    )

    pipeline._prefetch_weights(bp_dir)

    out_dir = bp_dir / ".mdp" / "weights"
    assert (out_dir / "config.json").exists()
    assert (out_dir / "model.safetensors").exists()
    assert (out_dir / "subdir" / "tokenizer.json").exists()
    assert [item[1] for item in downloaded] == ["config.json", "model.safetensors", "subdir/tokenizer.json"]


def test_prefetch_weights_hf_repo_cleans_hf_cache_dir(tmp_path, monkeypatch):
    bp_dir = tmp_path / "bp"
    bp_dir.mkdir()
    (bp_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (bp_dir / "blueprint.yaml").write_text(
        """
name: weight-hf-repo-clean-cache
provider: local
build:
  weights:
    - https://huggingface.co/ZhengPeng7/BiRefNet_dynamic
deploy:
  providers:
    - name: local
""".strip()
        + "\n",
        encoding="utf-8",
    )

    def fake_list_repo_files(repo_id, repo_type, revision=None, token=None):
        assert repo_id == "ZhengPeng7/BiRefNet_dynamic"
        assert repo_type == "model"
        assert revision is None
        assert token is None
        return ["model.safetensors"]

    def fake_hf_hub_download(
        repo_id,
        filename,
        repo_type,
        revision,
        local_dir,
        local_dir_use_symlinks,
        token=None,
    ):
        _ = (repo_id, filename, repo_type, revision, local_dir_use_symlinks, token)
        out_dir = Path(local_dir)
        (out_dir / filename).write_bytes(b"x")
        cache_meta = out_dir / ".cache" / "huggingface" / "download" / "foo.metadata"
        cache_meta.parent.mkdir(parents=True, exist_ok=True)
        cache_meta.write_text("meta", encoding="utf-8")
        return str(out_dir / filename)

    monkeypatch.setattr(pipeline, "list_repo_files", fake_list_repo_files, raising=False)
    monkeypatch.setattr(pipeline, "hf_hub_download", fake_hf_hub_download, raising=False)

    pipeline._prefetch_weights(bp_dir)

    out_dir = bp_dir / ".mdp" / "weights"
    assert (out_dir / "model.safetensors").exists()
    assert not (out_dir / ".cache").exists()


def test_deploy_uses_last_build_image_when_image_not_provided(tmp_path, monkeypatch):
    bp_dir = tmp_path / "bp"
    bp_dir.mkdir()
    (bp_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (bp_dir / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (bp_dir / "service.py").write_text("print('ok')\n", encoding="utf-8")
    (bp_dir / "blueprint.yaml").write_text(
        """
name: last-build-rollout
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

    state_dir = bp_dir / ".mdp"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "last-build.json").write_text(
        '{"image":"repo/demo:abc123","provider":"local"}\n',
        encoding="utf-8",
    )

    captured = {}

    class FakeProvider:
        def rollout(self, _blueprint_dir, _bp, image, env):
            captured["image"] = image
            captured["env"] = env
            return "ok"

    monkeypatch.setattr(pipeline, "get_provider", lambda _: FakeProvider())
    result = pipeline.deploy(bp_dir, provider="local", image=None, env="prod")

    assert result == "ok"
    assert captured["image"] == "repo/demo:abc123"
    assert captured["env"] == "prod"


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
