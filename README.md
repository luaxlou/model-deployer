# Model Deployer

`model-deployer` 是一个无状态、目录驱动的模型部署 CLI。

核心定位：
- 一个 blueprint 目录就是一个部署单元
- 命令即流程，无需平台侧状态管理
- 本地优先（Docker），可逐步扩展到云 provider

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

mdp lint -d ./blueprints/example
mdp deploy -d ./blueprints/example
```

## AI 提示词（可复制）

把下面这段直接贴给 AI 助手，用于说明当前项目需求：

```text
当前项目要引入 mdp 工具（mdp 在本地已安装）。

使用说明请先阅读：
https://github.com/luaxlou/model-deployer
```

## 输入模型

统一输入：

```bash
mdp <subcommand> -d <blueprint_dir>
```

Blueprint 目录规范见：[`docs/blueprint-spec.md`](./docs/blueprint-spec.md)

## 多工具能力

### 1) 质量与规划

- `mdp lint -d <dir>`：校验 blueprint 文件、关键字段与必需文件
- `mdp plan -d <dir> [--out plan.json]`：输出执行计划与默认参数

### 2) 构建与发布

- `mdp build -d <dir>`：构建镜像并输出 image
- `mdp rollout -d <dir> --image <image>`：启动部署并输出 `endpoint/container_name/status`
- `mdp deploy -d <dir> [--build-only]`：默认执行 `build -> deploy -> verify`，加 `--build-only` 时仅执行 `build`

### 3) 验证

- `mdp verify -d <dir>`：执行健康检查 + 可选 `smoke.sh`

### 4) 观测与运维

- `mdp status -d <dir>`：查看当前部署状态
- `mdp logs -d <dir> [--tail 200]`：查看日志
- `mdp cost -d <dir> [--group-by deployment]`：成本视图（local 为 0）

## 默认参数与行为

全局默认：
- `provider`: 由 `blueprint.yaml` 的 `provider` 字段决定
- `--follow`: `true`
- `--env`: `prod`

`mdp deploy` 默认流水线（不带 `--build-only`）：
1. `build`
2. `deploy`
3. `verify`

自动行为：
- 若存在 `<blueprint_dir>/smoke.sh`，自动执行
- `weights` 从 `blueprint.yaml` 的 `build.model.weights` 读取
- local provider 自动选择可用主机端口，避免端口冲突

## 输出约定（无状态）

核心命令输出优先返回：
- `image`
- `status`
- `endpoint`
- `container_name`

不返回平台化状态字段（如 operation_id）。

## 失败返回码

- `0`：成功
- `2`：blueprint 校验失败
- `3`：构建失败
- `4`：部署失败
- `5`：验证失败
- `6`：回滚失败

## 示例工程（真实可实验小模型）

`blueprints/example` 内置真实训练的极小 sklearn 模型（`tiny_model.joblib`）。

常用命令：

```bash
mdp lint -d ./blueprints/example
mdp plan -d ./blueprints/example
mdp build -d ./blueprints/example
mdp deploy -d ./blueprints/example
```

一键 smoke：

```bash
make smoke
```

手动预测（将 `<endpoint>` 替换为 deploy 输出）：

```bash
curl -X POST <endpoint>/predict \
  -H "Content-Type: application/json" \
  -d '{"x1": 1.5, "x2": 0.2}'
```

## Provider 能力现状

- `local`：已实现，基于真实 Docker build/run/logs/inspect
- `eas`：当前兼容映射到 local 行为（占位）
- `pai`：已接入 JSON 配置更新模式（依赖 `aliyun` CLI + `blueprint.pai` 配置）

## PAI 使用说明（JSON 配置更新）

`provider: pai` 时，`mdp` 会读取 `pai.service_config` 指向的 JSON 文件，并调用：

- `aliyun pai UpdateService --Body file://<generated_json>`

其中，工具会在部署时自动覆盖 JSON 中的以下字段：
- `image`

其余运维命令仍由 `blueprint.yaml` 的命令模板控制：
- `pai.status_cmd`
- `pai.logs_cmd`
- `pai.cost_cmd`（可选）

可用变量：
- `{service_name}`
- `{region}`
- `{workspace_id}`
- `{tail}`
- `{group_by}`

示例：

```bash
mdp lint -d ./blueprints/pai-example
mdp deploy -d ./blueprints/pai-example
```
