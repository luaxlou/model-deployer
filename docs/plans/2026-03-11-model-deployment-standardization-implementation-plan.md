# Model Deployment Standardization Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an independent self-service model deployment platform with abstract provider interface and first production provider as Alibaba Cloud EAS.

**Architecture:** Implement a control-plane service with domain modules (image/model/deployment/debug/ops) and provider adapters. Keep core resources provider-agnostic and map to EAS via adapter. Expose both REST and MCP over the same application service boundary.

**Tech Stack:** Go 1.24, PostgreSQL, Redis (optional queue), OpenAPI, Docker Buildx, Prometheus, structured logging, Alibaba Cloud EAS/OSS adapters.

---

### Task 1: Bootstrap Independent Project Skeleton

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/README.md`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/go.mod`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/cmd/controlplane/main.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/router.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/Makefile`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/router_test.go`

**Step 1: Write the failing test**
```go
func TestHealthz(t *testing.T) {
    // expect /healthz returns 200
}
```

**Step 2: Run test to verify it fails**
Run: `go test ./... -run TestHealthz -v`
Expected: FAIL (handler/router missing)

**Step 3: Write minimal implementation**
```go
// register GET /healthz => 200 {"status":"ok"}
```

**Step 4: Run test to verify it passes**
Run: `go test ./... -run TestHealthz -v`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "chore: bootstrap control-plane skeleton"
```

### Task 2: Define Core Domain Specs and Validation

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/domain/spec/spec.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/domain/spec/validate.go`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/domain/spec/validate_test.go`

**Step 1: Write the failing test**
```go
func TestDeploymentSpecValidation(t *testing.T) {
    // missing digest/checksum should fail
}
```

**Step 2: Run test to verify it fails**
Run: `go test ./internal/domain/spec -v`
Expected: FAIL (validation not implemented)

**Step 3: Write minimal implementation**
```go
// Define BaseImage RuntimePack ModelArtifact WeightAsset ComputeProfile DeploymentSpec
// Validate required immutable fields
```

**Step 4: Run test to verify it passes**
Run: `go test ./internal/domain/spec -v`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "feat: add deployment spec domain model and validation"
```

### Task 3: Implement Provider Adapter Contract + EAS Stub

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/provider/provider.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/provider/eas/adapter.go`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/provider/eas/adapter_test.go`

**Step 1: Write the failing test**
```go
func TestEASAdapterImplementsProvider(t *testing.T) {
    // compile-time + runtime contract tests for Deploy/GetLogs/GetMetrics
}
```

**Step 2: Run test to verify it fails**
Run: `go test ./internal/provider/... -v`
Expected: FAIL (interface/stub absent)

**Step 3: Write minimal implementation**
```go
// Provider interface with BuildImage Deploy Scale Rollback GetLogs GetMetrics EstimateCost
// EAS adapter returns deterministic mocked payloads for now
```

**Step 4: Run test to verify it passes**
Run: `go test ./internal/provider/... -v`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "feat: add provider contract and eas adapter stub"
```

### Task 4: Deployment Service + Async Operation Tracking

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/deployment/service.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/operation/store.go`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/deployment/service_test.go`

**Step 1: Write the failing test**
```go
func TestCreateDeploymentReturnsOperationID(t *testing.T) {
    // create request should return operationId and pending status
}
```

**Step 2: Run test to verify it fails**
Run: `go test ./internal/service/... -v`
Expected: FAIL

**Step 3: Write minimal implementation**
```go
// enqueue operation + map deploymentRevision + invoke provider adapter
```

**Step 4: Run test to verify it passes**
Run: `go test ./internal/service/... -v`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "feat: add deployment service with async operation tracking"
```

### Task 5: REST API for Deployment/Debug/Ops (MVP)

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/handlers/deployments.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/handlers/debug.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/handlers/ops.go`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/handlers/handlers_test.go`

**Step 1: Write the failing test**
```go
func TestCreateDeploymentEndpoint(t *testing.T) {}
func TestDebugSessionInvokeEndpoint(t *testing.T) {}
func TestOpsCostQueryEndpoint(t *testing.T) {}
```

**Step 2: Run test to verify it fails**
Run: `go test ./internal/http/... -v`
Expected: FAIL

**Step 3: Write minimal implementation**
```go
// implement POST /deployments POST /debug/sessions/:id/invoke GET /ops/costs
```

**Step 4: Run test to verify it passes**
Run: `go test ./internal/http/... -v`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "feat: add mvp rest api handlers for deployment debug and ops"
```

### Task 6: MCP Tool Layer

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/mcp/tools.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/mcp/server.go`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/mcp/tools_test.go`

**Step 1: Write the failing test**
```go
func TestMCPDeployCreateMapsToService(t *testing.T) {}
```

**Step 2: Run test to verify it fails**
Run: `go test ./internal/mcp -v`
Expected: FAIL

**Step 3: Write minimal implementation**
```go
// map model.deploy.create/queryLogs/queryMetrics/queryCost to internal services
```

**Step 4: Run test to verify it passes**
Run: `go test ./internal/mcp -v`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "feat: add mcp tool facade for deployment and ops"
```

### Task 7: Image Service Management (Template/Build/Scan/Promote)

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/image/service.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/image/policy.go`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/image/service_test.go`

**Step 1: Write the failing test**
```go
func TestPromoteImageRequiresScanPass(t *testing.T) {}
```

**Step 2: Run test to verify it fails**
Run: `go test ./internal/service/image -v`
Expected: FAIL

**Step 3: Write minimal implementation**
```go
// image lifecycle: draft -> built -> scanned -> promoted
```

**Step 4: Run test to verify it passes**
Run: `go test ./internal/service/image -v`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "feat: add image management lifecycle and promotion policy"
```

### Task 8: Metrics/Logs/Cost Aggregation

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/ops/service.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/ops/cost.go`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/ops/service_test.go`

**Step 1: Write the failing test**
```go
func TestQueryCostGroupedByDeployment(t *testing.T) {}
```

**Step 2: Run test to verify it fails**
Run: `go test ./internal/service/ops -v`
Expected: FAIL

**Step 3: Write minimal implementation**
```go
// aggregate metrics/log pointers/cost by deploymentRevision and group dimensions
```

**Step 4: Run test to verify it passes**
Run: `go test ./internal/service/ops -v`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "feat: add ops aggregation for metrics logs and costs"
```

### Task 9: OpenAPI + Developer Docs + Smoke Tests

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/docs/openapi.yaml`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/docs/mcp-tools.md`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/scripts/smoke_eas.sh`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/scripts/smoke_eas.sh`

**Step 1: Write the failing test/check**
```bash
# smoke script should fail when required env vars are missing
```

**Step 2: Run check to verify it fails**
Run: `bash scripts/smoke_eas.sh`
Expected: FAIL with missing env var message

**Step 3: Write minimal implementation**
```bash
# add required env checks + simple create deployment -> query operation path
```

**Step 4: Run check to verify it passes**
Run: `EAS_ENDPOINT=... EAS_TOKEN=... bash scripts/smoke_eas.sh`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "docs: add openapi mcp docs and eas smoke script"
```

### Task 10: Final Verification Before Completion

**Files:**
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/README.md`

**Step 1: Run full tests**
Run: `go test ./... -v`
Expected: PASS

**Step 2: Run lint/static checks**
Run: `go vet ./...`
Expected: PASS

**Step 3: Run formatting**
Run: `gofmt -w $(find . -name '*.go')`
Expected: no diff after second run

**Step 4: Re-run tests**
Run: `go test ./... -v`
Expected: PASS

**Step 5: Commit**
```bash
git add .
git commit -m "chore: finalize mvp with verified test and docs status"
```
