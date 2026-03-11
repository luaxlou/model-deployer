package deployment

import (
	"context"
	"testing"

	"model-deploy-platform/internal/provider/eas"
	"model-deploy-platform/internal/service/operation"
)

func TestCreateDeploymentReturnsOperationID(t *testing.T) {
	svc := NewService(eas.NewAdapter(), operation.NewStore())
	resp, err := svc.CreateDeployment(context.Background(), CreateRequest{DeploymentID: "dep-1", Revision: "r1"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.OperationID == "" {
		t.Fatal("expected operation id")
	}
	if resp.Status != "pending" {
		t.Fatalf("expected pending, got %s", resp.Status)
	}
}
