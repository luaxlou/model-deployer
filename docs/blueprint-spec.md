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
  default: pai
  providers:
    - name: local
      health_path: /healthz
      health_port: 18080
      start_command: uvicorn service:app --host 0.0.0.0 --port 18080
    - name: pai
      region: cn-hangzhou
      workspace_id: "your-workspace-id"
      service_name: your-service
      endpoint: https://your-pai-endpoint.example.com
      image: registry.cn-hangzhou.aliyuncs.com/your-namespace/your-image:tag
      # image 为构建后推送仓库（公网地址）
      image: registry-vpc.cn-hangzhou.aliyuncs.com/your-public-namespace/your-image
      service_config: pai-service.json

verify:
  timeout_sec: 300
  interval_sec: 5
  script: smoke.sh

```

## 必填项

- `name`
- `build.model.weights[*].name`
- `build.model.weights[*].url`（必须是 `http/https`）
- `build` 对应文件存在（`Dockerfile`、`requirements.txt`、`service.py`）
- `deploy.providers` 至少配置一种部署方式（`name` 为 `local` / `eas` / `pai`）

当配置 `deploy.providers[].name = pai` 时，额外必填：
- `region`
- `workspace_id`
- `service_name`
- `image`（构建后推送公网仓库）
- `pai-service.json` 中必须包含私网拉取镜像字段（推荐 `containers[0].image`，兼容 `image`）
- `service_config`（JSON 文件路径，基于 blueprint 目录）

## 默认值

- `provider`: `local`
- `build.context`: `.`
- `build.dockerfile`: `Dockerfile`
- `build.requirements`: `requirements.txt`
- `build.service`: `service.py`
- `local` provider 默认：
  - `health_path`: `/healthz`
  - `health_port`: `8080`
  - `start_command`: `python service.py`
- `deploy.default`: `""`（为空时按命令参数/交互选择 provider）
- `verify.timeout_sec`: `300`
- `verify.interval_sec`: `5`
- `verify.script`: `""`（空字符串表示不执行脚本）
