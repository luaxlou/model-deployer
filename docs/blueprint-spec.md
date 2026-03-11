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

verify:
  timeout_sec: 300
  interval_sec: 5
```

## 必填项

- `name`
- `model.weights[*].name`
- `model.weights[*].url`（必须是 `http/https`）
- `build` 对应文件存在（`Dockerfile`、`requirements.txt`、`service.py`）

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
