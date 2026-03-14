import json

from mdp_cli.blueprint import Blueprint, BuildConfig, DeployConfig, PaiDeployConfig
from mdp_cli.providers import PaiProvider


def test_pai_build_image_uses_repo_base_and_release_tag(tmp_path, monkeypatch):
    provider = PaiProvider()
    bp = Blueprint(
        name="demo",
        build=BuildConfig(),
        deploy=DeployConfig(
            pai=PaiDeployConfig(
                image="registry.cn-hangzhou.aliyuncs.com/ns/demo:latest",
                region="cn-hangzhou",
                workspace_id="ws-1",
                service_name="svc",
                endpoint="https://example.com",
                eas_config="eas-service.json",
            )
        ),
    )

    calls = []
    monkeypatch.setattr("mdp_cli.providers._run_stream", lambda cmd, step: calls.append((step, cmd)))
    monkeypatch.setattr("mdp_cli.providers._run", lambda cmd: "ok")
    monkeypatch.setattr("mdp_cli.providers._release_tag", lambda: "abc12345")

    image = provider.build_image(tmp_path, bp)

    assert image == "mdp-demo:abc12345"
    assert any(step == "docker build" for step, _ in calls)
    assert not any(step == "docker push" for step, _ in calls)


def test_pai_push_image_tags_and_pushes(tmp_path, monkeypatch):
    provider = PaiProvider()
    bp = Blueprint(
        name="demo",
        build=BuildConfig(),
        deploy=DeployConfig(
            pai=PaiDeployConfig(
                image="registry.cn-hangzhou.aliyuncs.com/ns/demo:latest",
                region="cn-hangzhou",
                workspace_id="ws-1",
                service_name="svc",
                endpoint="https://example.com",
                eas_config="eas-service.json",
            )
        ),
    )

    run_calls = []
    stream_calls = []
    monkeypatch.setattr("mdp_cli.providers._run", lambda cmd: run_calls.append(cmd) or "ok")
    monkeypatch.setattr(
        "mdp_cli.providers._run_stream",
        lambda cmd, step: stream_calls.append((step, cmd)),
    )

    pushed = provider.push_image(tmp_path, bp, image="mdp-demo:abc12345")

    assert pushed == "registry.cn-hangzhou.aliyuncs.com/ns/demo:abc12345"
    assert any(call[:3] == ["docker", "tag", "mdp-demo:abc12345"] for call in run_calls)
    assert any(step == "docker push" for step, _ in stream_calls)


def test_pai_rollout_updates_eas_container_image_with_built_tag(tmp_path, monkeypatch):
    provider = PaiProvider()
    bp_dir = tmp_path / "bp"
    bp_dir.mkdir()
    eas_path = bp_dir / "eas-service.json"
    eas_path.write_text(
        json.dumps(
            {
                "containers": [
                    {"image": "registry-vpc.cn-hangzhou.aliyuncs.com/private-ns/demo:latest"}
                ]
            }
        ),
        encoding="utf-8",
    )

    bp = Blueprint(
        name="demo",
        build=BuildConfig(),
        deploy=DeployConfig(
            pai=PaiDeployConfig(
                region="cn-hangzhou",
                workspace_id="ws-1",
                service_name="svc",
                endpoint="https://example.com",
                image="registry.cn-hangzhou.aliyuncs.com/public-ns/demo",
                eas_config="eas-service.json",
            )
        ),
    )

    body = {}
    monkeypatch.setattr(provider, "_ensure_cli", lambda: None)

    def fake_run_with_heartbeat(cmd, step, interval_sec=5):
        _ = step
        _ = interval_sec
        body["cmd"] = cmd
        body["json"] = json.loads(cmd[cmd.index("--body") + 1])
        return "ok"

    monkeypatch.setattr("mdp_cli.providers._run_with_heartbeat", fake_run_with_heartbeat)

    provider.rollout(
        bp_dir,
        bp,
        image="registry.cn-hangzhou.aliyuncs.com/public-ns/demo:abc12345",
        env="prod",
    )

    assert body["cmd"][:3] == ["aliyun", "eas", "UpdateService"]
    assert "--ClusterId" in body["cmd"]
    assert body["cmd"][body["cmd"].index("--ClusterId") + 1] == "cn-hangzhou"
    assert "--ServiceName" in body["cmd"]
    assert "--body" in body["cmd"]
    assert body["json"]["containers"][0]["image"] == (
        "registry-vpc.cn-hangzhou.aliyuncs.com/private-ns/demo:abc12345"
    )
