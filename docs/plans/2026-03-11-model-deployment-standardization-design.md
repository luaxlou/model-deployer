# 模型部署标准化平台设计（独立项目）

**项目路径：** `/Users/john/workspace/luaxlou/model-deploy-platform`

## 1. 目标与范围

目标：构建一个对算法工程师友好的模型部署平台，统一管理基础镜像、Python 运行时、模型与权重、部署资源、在线调试、监控日志、费用与运维 API/MCP。

首发策略：
- 架构先抽象（Provider Adapter）
- 首个 Provider 落地阿里云 EAS
- 项目单独孵化，不依赖原工程代码

## 2. 总体架构

- `Control Plane`
  - 统一 API 网关（REST + MCP）
  - 鉴权、审计、异步任务编排
- `Domain Services`
  - Image Service
  - Model Registry Service
  - Deployment Service
  - Debug Service
  - Ops Service
- `Provider Adapter Layer`
  - 统一接口：`buildImage/deploy/scale/getLogs/getMetrics/estimateCost`
  - 首发实现：`EASAdapter`
- `Data Plane`
  - 镜像仓库（ACR/Harbor）
  - 权重存储（OSS）
  - 在线推理（EAS）
  - 指标与日志（Prometheus + SLS/ELK）

## 3. 核心资源模型

- `BaseImage`
  - `name`, `cuda`, `python`, `os`, `securityLevel`, `digest`
- `RuntimePack`
  - `requirements.lock`, `startupCmd`, `healthCheck`, `envSchema`
- `ModelArtifact`
  - `modelName`, `taskType`, `entrypoint`, `framework`, `artifactVersion`
- `WeightAsset`
  - `uri`, `checksum`, `size`, `license`, `encryption`
- `ComputeProfile`
  - `provider`, `instanceType`, `gpu`, `cpu`, `mem`, `autoscaling`, `spotPolicy`
- `Deployment`
  - `stage`, `trafficPolicy`, `rollbackTo`, `slaTier`, `budgetLimit`

版本可追溯链路：
`BaseImage@digest + RuntimePack@lock + ModelArtifact@version + WeightAsset@checksum + ComputeProfile@revision => DeploymentRevision`

## 4. API 与 MCP 设计

### 4.1 REST API（核心）

- 资源管理
  - `POST /base-images`
  - `POST /runtime-packs`
  - `POST /models`
  - `POST /weights`
  - `POST /deployments`
- 部署运维
  - `POST /deployments/:id/rollout`
  - `POST /deployments/:id/rollback`
  - `POST /deployments/:id/scale`
- 在线调试
  - `POST /debug/sessions`
  - `POST /debug/sessions/:id/invoke`
  - `GET /debug/sessions/:id/logs`
  - `POST /debug/sessions/:id/promote`
- 可观测/费用
  - `GET /ops/metrics`
  - `GET /ops/logs`
  - `GET /ops/costs`
  - `POST /ops/budgets`
  - `POST /ops/alerts`

### 4.2 MCP Tools（面向智能体）

- `model.deploy.create`
- `model.deploy.updateTraffic`
- `model.deploy.rollback`
- `model.debug.runCase`
- `model.ops.queryLogs`
- `model.ops.queryMetrics`
- `model.ops.queryCost`
- `model.image.promote`
- `model.image.scan`
- `model.weight.verify`

原则：MCP 与 REST 一一映射，所有写操作返回 `operationId`，支持异步追踪。

## 5. 镜像服务管理（重点）

- 基础镜像目录：按框架与 CUDA 版本维护官方模板
- 构建流水线：Dockerfile 规范检查、依赖锁定、漏洞扫描、签名
- 发布策略：`dev -> staging -> prod` 的镜像推广链
- 回滚：按 digest 回滚到历史稳定镜像
- 权限：镜像创建、推广、删除分级授权

## 6. EAS 首发 MVP 边界

MVP 只做闭环能力：
- 一键生成 EAS 服务（从 DeploymentSpec）
- 灰度发布、回滚、扩缩容
- 在线调试与候选版本提升
- 指标/日志/费用联查（按 DeploymentRevision）
- 预算与告警

暂不做：
- 多云实时调度
- 高级实验编排平台
- 复杂 FinOps 优化引擎

## 7. 风险与控制

- 抽象泄漏：通过 `providerCapabilities` 显式暴露能力矩阵
- 配置复杂：提供场景模板（检测/分割/多模态）
- 成本失控：prod 强制预算阈值与告警，支持自动降级策略

## 8. 验收标准（MVP）

- 新模型上线时间（不含大权重上传）<= 30 分钟
- 回滚时间 <= 5 分钟
- 95% 发布任务算法工程师可自助完成
- 监控/日志/费用均可按 DeploymentRevision 一键联查
