from pathlib import Path

from mdp_cli import pipeline


def test_deploy_build_only_skips_rollout_and_verify(monkeypatch):
    calls = []

    def fake_build(_dir: Path):
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
