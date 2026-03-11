# Blueprint 驱动的模型部署平台完整方案（EAS 首发，基础设施无关）

**项目路径：** `/Users/john/workspace/luaxlou/model-deploy-platform`

## 1. 背景与目标

目标是将模型部署流程标准化为单一入口 `Blueprint`，并由平台 `Deployer` 控制完整 CD 生命周期，优先提升工程效率：

- 上线时长（Submit -> Running）
- 回滚时长（Rollback Start -> Running）
- 自助率（无需平台/运维介入的成功部署比例）

约束与决策：

- 首发基础设施：阿里云 EAS
- 平台抽象：不限定云，可扩展到物理机或其他基础设施
- 发布策略：仅全量发布 + 回滚，长期不支持灰度
- 术语统一：只使用 `Blueprint`，不引入 Template/Manifest/Contract 别名

## 2. 参考实践映射（来自 cultural-annotation inference）

参考工程 `/Users/john/workspace/luaxlou/cultural-annotation/inference` 已验证以下关键实践：

1. 服务生命周期脚本化：create/update/start/stop/status/delete/watch
2. EAS 配置模板化：镜像、env、readiness probe、算力规格
3. 启动期模型拉取与缓存：按 URI 下载、checksum 校验、解压与复用
4. 最小验活流程：`/health` + 推理接口 smoke
5. 常见失败点：ACR/OSS 内外网地址不匹配、凭证/endpoint 失配、冷启动下载耗时

本方案将这些实践沉淀为平台内建能力，由 `Deployer` 执行，不再依赖项目级手工脚本流程。

## 3. 总体架构

### 3.1 分层

1. `API + MCP Gateway`
- 对外提供 Blueprint、部署、回滚、状态查询与效率指标。
- 所有写操作返回 `operationId`。

2. `Domain Core`
- 统一领域对象：Blueprint、Deployment、DeploymentRevision、Operation。
- 负责校验、状态机推进、审计追溯。

3. `Deployer`
- 平台部署编排器，负责构建、发布、验证、回滚全生命周期。
- 不直接绑定任何特定云。

4. `Infrastructure Adapter`
- 面向具体基础设施的适配层（首发 `EASAdapter`）。
- 仅负责基础设施动作，不承载业务编排。

5. `Artifact + Observability`
- 镜像与发布元数据归档。
- 日志/指标/成本按 `deploymentRevision` 聚合。

### 3.2 关键职责边界

- 用户提交：Blueprint 内容与目标环境参数
- 平台 Deployer：执行全链路 CD
- EAS：基础设施承载与运行，不承担业务发布编排

## 4. Blueprint 规范（固定模板）

`Blueprint` 是唯一部署入口，定义一次可追溯发布所需全部信息。

### 4.1 必填内容

1. `Dockerfile`
2. `requirements.txt`
3. Python 服务脚本
4. 模型代码
5. 模型权重下载地址（一个或多个 URI）

### 4.2 必填元数据

1. `entrypoint` / 启动命令
2. `healthCheck`（path/port/timeout）
3. `inferSmoke`（最小推理请求模板）
4. `weightAssets[].checksum`（建议升级为强制）
5. `targetProfile`（目标类型、资源规格、副本策略）

### 4.3 版本与追溯

生成不可变 revision 指纹：

`hash(Dockerfile + requirements + service scripts + model code + weight URIs/checksums + targetProfile)`

并写入 `DeploymentRevision`。

## 5. CD 生命周期（由 Deployer 固定控制）

### 5.1 状态机

`Submitted -> BuildingImage -> PushingArtifact -> DeployingInfra -> FetchingWeights -> BootstrappingService -> Verifying -> Running`

失败分支：任一阶段可转 `Failed`。

回滚分支：

`Running -> RollbackDeploying -> Verifying -> Running | Failed`

### 5.2 门禁规则（强制）

1. 构建门禁：Dockerfile 可构建、requirements 可安装、入口存在
2. 权重门禁：URI 可访问、checksum 匹配
3. 部署门禁：镜像可拉取、目标资源满足、健康检查配置有效
4. 发布门禁：health 通过 + 至少 1 次推理 smoke 成功
5. 回滚门禁：必须存在可回滚的历史 Running revision

### 5.3 无灰度原则

- 不支持 canary/traffic split
- rollout 恒为全量替换
- rollback 恒为 revision 级回退

## 6. API 与 MCP 设计（精简版）

### 6.1 REST

1. `POST /blueprints`
2. `GET /blueprints/{id}`
3. `POST /deployments`（引用 `blueprintId`）
4. `POST /deployments/{id}/rollout`
5. `POST /deployments/{id}/rollback`
6. `GET /deployments/{id}/revisions`
7. `GET /operations/{operationId}`
8. `GET /ops/efficiency`

### 6.2 MCP

1. `model.blueprint.create`
2. `model.blueprint.get`
3. `model.deploy.create`
4. `model.deploy.rollout`
5. `model.deploy.rollback`
6. `model.operation.get`
7. `model.ops.efficiency.query`

REST 与 MCP 一一映射，保证人机操作一致性。

## 7. EAS 首发落地方式（基础设施适配）

EAS 相关字段封装在 `EASAdapter`，包括：

- 服务创建/更新/启停/删除
- readiness probe 映射
- env 注入（权重 URI、凭据引用、启动命令）
- 状态拉取与实例日志查询

同时将参考工程的实战规则平台化：

1. ACR push/pull 内外网地址区分检查
2. OSS endpoint 与地域一致性检查
3. 权重下载失败分类（鉴权、网络、checksum、解压）
4. 冷启动缓存命中标识与耗时采集

## 8. 数据与审计模型

核心对象：

1. `Blueprint`
2. `Deployment`
3. `DeploymentRevision`
4. `Operation`
5. `OperationEvent`

审计要求：

- 任一部署可追溯到 Blueprint 内容摘要、镜像 digest、权重 URI/checksum、目标环境、操作人、时间线。
- 回滚操作必须记录：触发人、原因、目标 revision、结果。

## 9. 工程效率验收标准（首期）

1. `T_submit_to_running`：P50 <= 30 分钟（不含超大权重首次上传）
2. `T_rollback`：P50 <= 5 分钟
3. `SelfServiceSuccessRate`：>= 95%
4. `OperationTraceCompleteness`：100% 写操作可追踪到 operation 事件流

## 10. 里程碑

### P0（闭环可用）

- Blueprint 提交
- 平台内 Docker 构建与产物入库
- EAS 适配部署
- Operation 状态机
- health + smoke 验证
- rollback 路径

### P1（稳定性与可用性）

- 权重下载重试与错误分类
- 失败诊断增强（分阶段错误码）
- 效率指标面板
- Blueprint 校验器增强

### P2（基础设施扩展）

- 在不变更 Blueprint 语义的前提下接入物理机/其他基础设施适配器

## 11. 非目标（明确不做）

1. 灰度发布、流量分流
2. 多云智能调度
3. 高级实验编排平台

---

该方案确保：

- 对用户是固定模板输入（Blueprint）
- 对平台是受控 CD 生命周期（Deployer）
- 对基础设施是可替换适配层（EAS 首发，不限定未来物理机）
