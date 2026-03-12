# Blueprint 与 Dockerfile 职责去重设计

日期：2026-03-12

## 1. 背景与目标

当前 `blueprint.yaml` 与 `Dockerfile` 在运行入口、依赖与代码路径上存在重复描述，导致：
- 配置漂移（两个来源不一致）
- 行为不透明（用户不清楚最终以谁为准）
- 维护成本高（文档、样例、校验多处联动）

本次目标：将 `Dockerfile` 设为构建与运行的唯一事实来源，`blueprint.yaml` 只保留编排与平台参数。

## 2. 职责边界

### 2.1 Dockerfile 负责
- 依赖安装
- 应用文件布局
- 运行入口（`ENTRYPOINT`/`CMD`）
- 容器内端口约定

### 2.2 blueprint.yaml 负责
- 构建输入：`build.context`、`build.dockerfile`
- 外部模型制品：`build.model.weights[*]`
- 部署平台参数：`deploy.providers[*]`、`deploy.pai.*`
- 验证策略：`verify.*`

## 3. Schema 变更

### 3.1 删除字段
- `build.requirements`
- `build.service`
- `build.model.code`
- `deploy.providers[].start_command`

### 3.2 保留字段
- `build.context`
- `build.dockerfile`
- `build.model.weights[*]`
- `deploy.providers[].health_path`
- `deploy.providers[].health_port`
- `deploy.pai.*`
- `verify.*`

## 4. 运行行为变更

### 4.1 local rollout
- 变更前：可通过 `start_command` 覆盖镜像默认入口
- 变更后：始终执行镜像默认入口，不再注入覆盖命令

### 4.2 pai rollout
- 继续基于 `eas_config` 更新服务镜像
- `blueprint` 不再声明启动命令

## 5. 校验与兼容策略

### 5.1 lint/validate 规则
- 不再校验 `requirements/service/model.code` 对应文件存在性
- 继续校验 `build.dockerfile`、`build.context`、weights 与 provider 配置
- 若出现已删除字段，`lint` 直接失败并给出字段级错误提示

### 5.2 兼容策略
- 采用严格迁移，不做 silent fallback
- 不保留双写模式，避免旧配置继续扩散

## 6. 落地改动清单

### 6.1 代码
- `mdp_cli/blueprint.py`
  - 移除已废弃字段的数据结构与解析逻辑
  - 新增废弃字段检测与报错
- `mdp_cli/providers.py`
  - `LocalProvider.rollout` 删除 `start_command` 注入逻辑

### 6.2 文档与样例
- 更新 `docs/blueprint-spec.md`
- 更新 `blueprints/example/blueprint.yaml`
- 更新 `blueprints/pai-example/blueprint.yaml`
- 在 `README.md` 增加 breaking change 说明（启动命令迁移至 Dockerfile）

### 6.3 测试
- 更新 `tests/test_blueprint.py`
  - 成功用例适配新 schema
  - 增加废弃字段失败用例
- 视需要更新 `tests/test_pipeline.py`
  - 断言 local rollout 不再注入覆盖命令

## 7. 验证命令

```bash
pytest -q
python3 -m mdp_cli.main lint -d ./blueprints/example
python3 -m mdp_cli.main lint -d ./blueprints/pai-example
```

