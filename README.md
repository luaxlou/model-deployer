# Model Deploy Tool

Stateless CLI for blueprint-driven model deployment.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
mdp lint -d ./blueprints/example
mdp deploy -d ./blueprints/example
```

## CLI Usage

`mdp` 采用目录输入模式，默认最少参数可执行：

```bash
mdp <subcommand> -d <blueprint_dir>
```

Blueprint 目录规范见：[`docs/blueprint-spec.md`](./docs/blueprint-spec.md)

### 全局默认
- `-d` 必填：`<blueprint_dir>`
- `--provider` 默认：`local`
- `--follow` 默认：`true`
- `--on-fail` 默认：`rollback`
- `--env` 默认：`prod`

### deploy 默认流水线
不额外传参时，`mdp deploy` 自动执行：

1. `lint`
2. `build`
3. `rollout`
4. `verify`

### blueprint.yaml 字段默认
- `build.context`：`.`
- `build.dockerfile`：`Dockerfile`
- `build.requirements`：`requirements.txt`
- `build.service`：`service.py`
- `deploy.health_path`：`/healthz`
- `deploy.health_port`：`18080`（示例）
- `deploy.start_command`：`uvicorn service:app --host 0.0.0.0 --port 18080`（示例）
- `verify.timeout_sec`：`300`
- `verify.interval_sec`：`5`

### 自动行为
- 若存在 `<blueprint_dir>/smoke.sh`，自动执行 smoke；不存在则跳过。
- `weights` 从 `blueprint.yaml` 的 `model.weights` 读取，不再依赖额外文件。
- local provider 自动选择可用主机端口，避免端口冲突。

### 最简执行
```bash
mdp deploy -d ./blueprints/bert-prod
```

等价于：

```bash
mdp deploy -d ./blueprints/bert-prod --provider local --follow --on-fail rollback --env prod
```

### 失败返回码
- `0`：成功
- `2`：blueprint 校验失败
- `3`：构建失败
- `4`：部署失败
- `5`：验证失败
- `6`：回滚失败

## 示例 Blueprint 目录

仓库内提供了可直接执行的示例目录：

```bash
mdp lint -d ./blueprints/example
mdp plan -d ./blueprints/example
mdp build -d ./blueprints/example
mdp deploy -d ./blueprints/example
```

或运行一键 smoke：

```bash
make smoke
```

## 本地极小模型验证

示例工程 `blueprints/example` 内置了一个真实训练的极小 sklearn 模型（`TinySklearnModel` + `tiny_model.joblib`），用于本地 Docker 部署链路测试。

1. 执行完整部署（会自动 `docker build` + `docker run`）：

```bash
mdp deploy -d ./blueprints/example --provider local
```

2. 手动预测测试：

```bash
curl -X POST http://127.0.0.1:18080/predict \
  -H "Content-Type: application/json" \
  -d '{"x1": 1.5, "x2": 0.2}'
```

## Core Features
- Blueprint 目录输入（单目录即单部署单元）
- 无状态命令执行（不依赖平台侧状态管理）
- 默认流水线：`lint -> build -> rollout -> verify`
- 失败自动回滚（默认 `--on-fail rollback`）
- local provider 适配（Docker 本地执行）
