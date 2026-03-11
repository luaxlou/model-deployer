package mcp

import (
	"context"
	"testing"

	"model-deploy-platform/internal/provider/eas"
	"model-deploy-platform/internal/service/deployment"
	"model-deploy-platform/internal/service/operation"
	"model-deploy-platform/internal/service/ops"
)

func TestMCPDeployCreateMapsToService(t *testing.T) {
	p := eas.NewAdapter()
	tools := Tools{
		Deployment: deployment.NewService(p, operation.NewStore()),
		Ops:        ops.NewService(p),
	}
	resp, err := tools.DeployCreate(context.Background(), "dep-1", "r1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.OperationID == "" {
		t.Fatal("expected operation id")
	}
}
