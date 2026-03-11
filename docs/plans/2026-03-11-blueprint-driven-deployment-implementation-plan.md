# Blueprint-Driven Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Blueprint-driven deployment control-plane where Deployer owns full CD lifecycle (build, deploy, verify, rollback) with EAS as the first infrastructure adapter.

**Architecture:** Introduce a single `Blueprint` domain model as deployment input, then orchestrate lifecycle via a `Deployer` service and operation state machine. Keep infrastructure concerns inside adapters (EAS first) and expose consistent REST + MCP APIs with operation tracking and efficiency metrics.

**Tech Stack:** Go 1.24, net/http, existing internal service layering, Docker/Buildx invocation wrapper, Alibaba Cloud EAS adapter, OpenAPI docs, shell smoke scripts.

---

### Task 1: Add Blueprint Domain Model and Validation

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/domain/blueprint/blueprint.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/domain/blueprint/validate.go`
- Test: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/domain/blueprint/validate_test.go`

**Step 1: Write the failing test**

```go
func TestValidateBlueprint_RequiresDockerfileRequirementsServiceModelAndWeights(t *testing.T) {
	bp := Blueprint{}
	if err := Validate(bp); err == nil {
		t.Fatal("expected validation error")
	}
}
```

**Step 2: Run test to verify it fails**

Run: `go test ./internal/domain/blueprint -v`
Expected: FAIL (package/files missing)

**Step 3: Write minimal implementation**

```go
type Blueprint struct {
	ID                string
	Dockerfile        string
	RequirementsTxt   string
	ServiceScriptPath string
	ModelSourcePath   string
	WeightAssets      []WeightAsset
	StartCommand      string
	HealthPath        string
	HealthPort        int
	SmokePath         string
}
```

```go
func Validate(bp Blueprint) error {
	if bp.Dockerfile == "" || bp.RequirementsTxt == "" || bp.ServiceScriptPath == "" || bp.ModelSourcePath == "" {
		return errors.New("missing required blueprint sources")
	}
	if len(bp.WeightAssets) == 0 {
		return errors.New("at least one weight asset is required")
	}
	return nil
}
```

**Step 4: Run test to verify it passes**

Run: `go test ./internal/domain/blueprint -v`
Expected: PASS

**Step 5: Commit**

```bash
git add internal/domain/blueprint
git commit -m "feat(domain): add blueprint model and validation"
```

### Task 2: Extend Operation Store for Lifecycle Stages

**Files:**
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/operation/store.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/operation/store_test.go`

**Step 1: Write the failing test**

```go
func TestOperationStore_TracksStageTransitions(t *testing.T) {
	store := NewStore()
	store.Save(Operation{ID: "op-1", Status: StatusPending, Stage: StageSubmitted})
	if err := store.UpdateStage("op-1", StageBuildingImage, StatusRunning, "building"); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}
```

**Step 2: Run test to verify it fails**

Run: `go test ./internal/service/operation -v`
Expected: FAIL (`Stage`/`UpdateStage` missing)

**Step 3: Write minimal implementation**

```go
type Stage string
const (
	StageSubmitted Stage = "submitted"
	StageBuildingImage Stage = "building_image"
	StageVerifying Stage = "verifying"
)

type Operation struct {
	ID      string
	Status  Status
	Stage   Stage
	Message string
}
```

```go
func (s *Store) UpdateStage(id string, stage Stage, status Status, msg string) error {
	// lookup, mutate stage/status/message, save back
}
```

**Step 4: Run test to verify it passes**

Run: `go test ./internal/service/operation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add internal/service/operation
git commit -m "feat(operation): track lifecycle stage transitions"
```

### Task 3: Introduce Infrastructure Adapter Contract (EAS as Implementation)

**Files:**
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/provider/provider.go`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/provider/eas/adapter.go`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/provider/eas/adapter_test.go`

**Step 1: Write the failing test**

```go
func TestEASAdapter_ImplementsInfrastructureAdapter(t *testing.T) {
	var _ provider.InfrastructureAdapter = (*Adapter)(nil)
}
```

**Step 2: Run test to verify it fails**

Run: `go test ./internal/provider/... -v`
Expected: FAIL (`InfrastructureAdapter` missing)

**Step 3: Write minimal implementation**

```go
type InfrastructureAdapter interface {
	Deploy(ctx context.Context, req DeployRequest) (DeployResponse, error)
	Rollback(ctx context.Context, req RollbackRequest) error
	Scale(ctx context.Context, req ScaleRequest) error
	GetLogs(ctx context.Context, deploymentID string) ([]string, error)
	GetMetrics(ctx context.Context, req MetricsQuery) (MetricsResponse, error)
	EstimateCost(ctx context.Context, req CostQuery) (CostResponse, error)
}
```

```go
type Adapter struct{}
// keep deterministic mocked returns for now, but satisfy new interface naming
```

**Step 4: Run test to verify it passes**

Run: `go test ./internal/provider/... -v`
Expected: PASS

**Step 5: Commit**

```bash
git add internal/provider
git commit -m "refactor(provider): introduce infrastructure adapter contract"
```

### Task 4: Add Build Service for Platform-Side Docker Build

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/build/service.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/build/executor.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/build/service_test.go`

**Step 1: Write the failing test**

```go
func TestBuildService_BuildFromBlueprintSources(t *testing.T) {
	exec := &fakeExecutor{imageRef: "registry.local/model@sha256:abc"}
	svc := NewService(exec)
	ref, err := svc.Build(context.Background(), BuildRequest{BlueprintID: "bp-1", ContextDir: "/tmp/ctx", DockerfilePath: "Dockerfile"})
	if err != nil || ref == "" { t.Fatal("expected image ref") }
}
```

**Step 2: Run test to verify it fails**

Run: `go test ./internal/service/build -v`
Expected: FAIL (package/files missing)

**Step 3: Write minimal implementation**

```go
type Executor interface {
	BuildImage(ctx context.Context, contextDir, dockerfilePath, imageTag string) (string, error)
}

type Service struct { exec Executor }
```

```go
func (s *Service) Build(ctx context.Context, req BuildRequest) (string, error) {
	return s.exec.BuildImage(ctx, req.ContextDir, req.DockerfilePath, req.ImageTag)
}
```

**Step 4: Run test to verify it passes**

Run: `go test ./internal/service/build -v`
Expected: PASS

**Step 5: Commit**

```bash
git add internal/service/build
git commit -m "feat(build): add platform-side docker build service"
```

### Task 5: Implement Deployer Lifecycle Service

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/deployer/service.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/deployer/service_test.go`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/deployment/service.go`

**Step 1: Write the failing test**

```go
func TestDeployer_RunLifecycleToRunning(t *testing.T) {
	// fake build + fake adapter + fake verifier
	// expect stages: submitted -> building_image -> deploying_infra -> verifying -> running
}
```

**Step 2: Run test to verify it fails**

Run: `go test ./internal/service/deployer -v`
Expected: FAIL (`Deployer` service missing)

**Step 3: Write minimal implementation**

```go
type Service struct {
	build BuildService
	infra provider.InfrastructureAdapter
	ops   *operation.Store
	verify Verifier
}

func (s *Service) Run(ctx context.Context, req RunRequest) (operation.Operation, error) {
	// create operation
	// stage: building_image
	// stage: deploying_infra
	// stage: verifying
	// stage: running(done)
}
```

**Step 4: Run test to verify it passes**

Run: `go test ./internal/service/deployer -v`
Expected: PASS

**Step 5: Commit**

```bash
git add internal/service/deployer internal/service/deployment/service.go
git commit -m "feat(deployer): orchestrate blueprint lifecycle stages"
```

### Task 6: Add Rollback on Deployer with Revision Guard

**Files:**
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/deployer/service.go`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/deployer/service_test.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/deployer/revision_store.go`

**Step 1: Write the failing test**

```go
func TestRollback_FailsWhenNoRunningRevision(t *testing.T) {
	// expect explicit error when rollback target not found
}
```

**Step 2: Run test to verify it fails**

Run: `go test ./internal/service/deployer -v -run Rollback`
Expected: FAIL (`Rollback` missing)

**Step 3: Write minimal implementation**

```go
func (s *Service) Rollback(ctx context.Context, req RollbackRequest) (operation.Operation, error) {
	// load target revision
	// deploy existing image digest without rebuild
	// verify then mark running
}
```

**Step 4: Run test to verify it passes**

Run: `go test ./internal/service/deployer -v -run Rollback`
Expected: PASS

**Step 5: Commit**

```bash
git add internal/service/deployer
git commit -m "feat(deployer): add full rollback flow with revision guard"
```

### Task 7: Expand REST API for Blueprint, Operation, Rollout, Rollback

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/handlers/blueprints.go`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/handlers/deployments.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/handlers/operations.go`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/router.go`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/handlers/handlers_test.go`

**Step 1: Write the failing test**

```go
func TestCreateBlueprintEndpoint(t *testing.T) {}
func TestRolloutEndpointReturnsOperationID(t *testing.T) {}
func TestRollbackEndpointReturnsOperationID(t *testing.T) {}
func TestGetOperationEndpoint(t *testing.T) {}
```

**Step 2: Run test to verify it fails**

Run: `go test ./internal/http/... -v`
Expected: FAIL (routes/handlers missing)

**Step 3: Write minimal implementation**

```go
// POST /blueprints
// POST /deployments/{id}/rollout
// POST /deployments/{id}/rollback
// GET /operations/{id}
```

**Step 4: Run test to verify it passes**

Run: `go test ./internal/http/... -v`
Expected: PASS

**Step 5: Commit**

```bash
git add internal/http
git commit -m "feat(http): add blueprint rollout rollback and operation endpoints"
```

### Task 8: Add MCP Tools for Blueprint + Deployment Lifecycle

**Files:**
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/mcp/tools.go`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/mcp/tools_test.go`

**Step 1: Write the failing test**

```go
func TestMCPBlueprintCreateMapsToService(t *testing.T) {}
func TestMCPDeployRollbackMapsToService(t *testing.T) {}
func TestMCPOperationGetMapsToStore(t *testing.T) {}
```

**Step 2: Run test to verify it fails**

Run: `go test ./internal/mcp -v`
Expected: FAIL (new tool methods missing)

**Step 3: Write minimal implementation**

```go
func (t Tools) BlueprintCreate(...) (..., error) { ... }
func (t Tools) DeployRollback(...) (..., error) { ... }
func (t Tools) OperationGet(...) (..., error) { ... }
```

**Step 4: Run test to verify it passes**

Run: `go test ./internal/mcp -v`
Expected: PASS

**Step 5: Commit**

```bash
git add internal/mcp
git commit -m "feat(mcp): add blueprint and lifecycle tools"
```

### Task 9: Add Efficiency Metrics Service and Endpoint

**Files:**
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/efficiency/service.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/service/efficiency/service_test.go`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/handlers/efficiency.go`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/internal/http/router.go`

**Step 1: Write the failing test**

```go
func TestEfficiencyStats_ComputesSubmitToRunningRollbackAndSelfServiceRate(t *testing.T) {}
```

**Step 2: Run test to verify it fails**

Run: `go test ./internal/service/efficiency -v`
Expected: FAIL (package/files missing)

**Step 3: Write minimal implementation**

```go
type Stats struct {
	SubmitToRunningP50Sec int64
	RollbackP50Sec        int64
	SelfServiceRate       float64
}
```

```go
// GET /ops/efficiency returns Stats JSON
```

**Step 4: Run test to verify it passes**

Run: `go test ./internal/service/efficiency -v && go test ./internal/http/... -v`
Expected: PASS

**Step 5: Commit**

```bash
git add internal/service/efficiency internal/http
git commit -m "feat(ops): add engineering efficiency metrics"
```

### Task 10: Update OpenAPI + MCP Docs + Smoke Script for Blueprint Flow

**Files:**
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/docs/openapi.yaml`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/docs/mcp-tools.md`
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/scripts/smoke_eas.sh`
- Create: `/Users/john/workspace/luaxlou/model-deploy-platform/scripts/smoke_blueprint.sh`

**Step 1: Write the failing check**

```bash
bash scripts/smoke_blueprint.sh
# expected to fail first because endpoints and required env checks are not complete
```

**Step 2: Run check to verify it fails**

Run: `bash scripts/smoke_blueprint.sh`
Expected: FAIL with missing env/endpoint message

**Step 3: Write minimal implementation**

```bash
# create blueprint -> create deployment -> rollout -> query operation -> query efficiency
```

**Step 4: Run check to verify it passes**

Run: `CONTROLPLANE_URL=http://localhost:8080 bash scripts/smoke_blueprint.sh`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/openapi.yaml docs/mcp-tools.md scripts/smoke_eas.sh scripts/smoke_blueprint.sh
git commit -m "docs(smoke): cover blueprint-driven lifecycle api and mcp"
```

### Task 11: Final Verification and Readme Refresh

**Files:**
- Modify: `/Users/john/workspace/luaxlou/model-deploy-platform/README.md`

**Step 1: Run full tests**

Run: `go test ./... -v`
Expected: PASS

**Step 2: Run static checks**

Run: `go vet ./...`
Expected: PASS

**Step 3: Run formatting**

Run: `gofmt -w $(find . -name '*.go')`
Expected: complete without error

**Step 4: Re-run tests after formatting**

Run: `go test ./... -v`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md
# include gofmt changes if any
git add $(find . -name '*.go')
git commit -m "chore: finalize blueprint-driven deployment implementation"
```
