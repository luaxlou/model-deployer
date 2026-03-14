# Blueprint 目录规范

输入单元是单个目录：`-d <blueprint_dir>`。

## 最小目录

```text
<blueprint_dir>/
  blueprint.yaml
  Dockerfile
```

## 可选内容

```text
<blueprint_dir>/
  smoke.sh
```

## blueprint.yaml 示例

```yaml
name: bert-prod
provider: local

build:
  context: .
  dockerfile: Dockerfile
  weights:
    - https://example.com/model.bin

deploy:
  default: pai
  providers:
    - name: local
      health_path: /healthz
      health_port: 18080
    - name: pai
      region: cn-hangzhou
      workspace_id: "your-workspace-id"
      service_name: your-service
      endpoint: https://your-pai-endpoint.example.com
      image: registry.cn-hangzhou.aliyuncs.com/your-namespace/your-image:tag
      # image 为构建后推送仓库（公网地址）
      image: registry-vpc.cn-hangzhou.aliyuncs.com/your-public-namespace/your-image
      eas_config: eas-service.json

verify:
  timeout_sec: 300
  interval_sec: 5
  script: smoke.sh

```

## 必填项

- `name`
- `build.weights[*]`（必须是 `http/https` URL 字符串）
  - 当 URL 是 Hugging Face 仓库根地址（例如 `https://huggingface.co/<org>/<repo>` 或 `.../tree/<revision>`）时，构建前会通过 `huggingface_hub` 按仓库文件列表逐个下载（建议先执行 `huggingface-cli login`）
- `build.dockerfile` 对应文件存在（`Dockerfile`）
- `deploy.providers` 至少配置一种部署方式（`name` 为 `local` / `eas` / `pai`）

当配置 `deploy.providers[].name = pai` 时，额外必填：
- `region`
- `workspace_id`
- `service_name`
- `image`（构建后推送公网仓库，建议填写仓库前缀不带 tag）
- `eas-service.json` 中必须包含私网拉取镜像字段（推荐 `containers[0].image`，兼容 `image`）
- `eas_config`（JSON 文件路径，基于 blueprint 目录）

## 默认值

- `provider`: `local`
- `build.context`: `.`
- `build.dockerfile`: `Dockerfile`
- `local` provider 默认：
  - `health_path`: `/healthz`
  - `health_port`: `8080`
- `deploy.default`: `""`（为空时按命令参数/交互选择 provider）
- `verify.timeout_sec`: `300`
- `verify.interval_sec`: `5`
- `verify.script`: `""`（空字符串表示不执行脚本）

## 约束

- 运行入口（启动命令）必须在镜像的 `ENTRYPOINT`/`CMD` 中定义。
- build 阶段产出的镜像 tag 规则为：`<git-sha-8>`（不可用时回退 timestamp）。
- deploy(pai) 会将 build 产出的 tag 自动同步到 `eas_config` 的镜像字段。
- 以下字段已移除，出现即 lint 失败：
  - `build.requirements`
  - `build.service`
  - `build.model.code`
  - `build.model.weights`
  - `deploy.providers[].start_command`
