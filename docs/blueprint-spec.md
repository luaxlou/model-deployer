# Blueprint 目录规范

输入单元是单个目录：`-d <blueprint_dir>`。

## 最小目录

```text
<blueprint_dir>/
  blueprint.yaml
  Dockerfile
  requirements.txt
  service.py
```

## 可选内容

```text
<blueprint_dir>/
  model/model.py
  smoke.sh
```

## blueprint.yaml 示例

```yaml
name: bert-prod
provider: local

build:
  context: .
  dockerfile: Dockerfile
  requirements: requirements.txt
  service: service.py
  model:
    code: model/model.py
    weights:
      - name: model-weights
        url: https://example.com/model.bin
        sha256: "optional"

deploy:
  health_path: /healthz
  health_port: 18080
  start_command: uvicorn service:app --host 0.0.0.0 --port 18080
  pai:
    region: cn-hangzhou
    workspace_id: "your-workspace-id"
    service_name: your-service
    endpoint: https://your-pai-endpoint.example.com
    image: registry.cn-hangzhou.aliyuncs.com/your-namespace/your-image:tag
    # image_repo 与 image 二选一；使用 image_repo 时，工具会构建并 push
    image_repo: registry.cn-hangzhou.aliyuncs.com/your-namespace/your-image
    service_config: pai-service.json
    status_cmd: "aliyun pai GetService --RegionId {region} --WorkspaceId {workspace_id} --ServiceName {service_name}"
    logs_cmd: "aliyun pai ListServiceLogs --RegionId {region} --WorkspaceId {workspace_id} --ServiceName {service_name} --PageSize {tail}"
    cost_cmd: "aliyun pai QueryServiceCost --RegionId {region} --WorkspaceId {workspace_id} --ServiceName {service_name}"

verify:
  timeout_sec: 300
  interval_sec: 5
  script: smoke.sh

```

## 必填项

- `name`
- `provider`（`local` / `eas` / `pai`）
- `build.model.weights[*].name`
- `build.model.weights[*].url`（必须是 `http/https`）
- `build` 对应文件存在（`Dockerfile`、`requirements.txt`、`service.py`）

当 `provider: pai` 时，额外必填：
- `deploy.pai.region`
- `deploy.pai.workspace_id`
- `deploy.pai.service_name`
- `deploy.pai.image` 或 `deploy.pai.image_repo`
- `deploy.pai.service_config`（JSON 文件路径，基于 blueprint 目录）
- `deploy.pai.status_cmd`
- `deploy.pai.logs_cmd`

## 默认值

- `provider`: `local`
- `build.context`: `.`
- `build.dockerfile`: `Dockerfile`
- `build.requirements`: `requirements.txt`
- `build.service`: `service.py`
- `deploy.health_path`: `/healthz`
- `deploy.health_port`: `18080`（示例）
- `deploy.start_command`: `uvicorn service:app --host 0.0.0.0 --port 18080`（示例）
- `verify.timeout_sec`: `300`
- `verify.interval_sec`: `5`
- `verify.script`: `""`（空字符串表示不执行脚本）
