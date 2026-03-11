# Glow 引入提示词（可直接复制）

来源：`glow` 最新 README 提示词风格（任务先行 + 文档先读 + 收益导向）。

参考链接：
- https://github.com/luaxlou/glow/blob/main/README.md
- https://github.com/luaxlou/glow/blob/main/docs/ai_coding_guide.md

## 提示词：在现有项目中引入 glow

```text
请在现有项目中引入 glow starter。
请先阅读：https://github.com/luaxlou/glow/blob/main/docs/ai_coding_guide.md
目标：迁移到 glow 的统一接入范式，减少重复样板并提升长期可维护性。
重点收益：让项目获得边界清晰、可组合复用、低心智负担和稳定约定。
需解决问题：如何把接入过程沉淀为可持续演进的工程基线。
输出要求：给出实施步骤、受影响文件清单、收益说明与验证结果。
完成后执行并反馈：go test ./... && go vet ./...
```

## 使用建议

1. 优先用于“存量 Go 服务接入 glow”的任务。
2. 提示词执行后，检查输出是否覆盖：
- 接入计划
- 改动文件清单
- 设计哲学收益说明
- `go test ./...` 与 `go vet ./...` 结果
