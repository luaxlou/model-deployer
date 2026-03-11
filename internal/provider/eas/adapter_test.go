package eas

import (
	"context"
	"testing"

	"model-deploy-platform/internal/provider"
)

func TestEASAdapterImplementsProvider(t *testing.T) {
	var p provider.Provider = NewAdapter()
	if _, err := p.Deploy(context.Background(), provider.DeployRequest{DeploymentID: "d1", Revision: "r1"}); err != nil {
		t.Fatalf("deploy failed: %v", err)
	}
	if _, err := p.GetLogs(context.Background(), "d1"); err != nil {
		t.Fatalf("logs failed: %v", err)
	}
	if _, err := p.GetMetrics(context.Background(), provider.MetricsQuery{DeploymentID: "d1"}); err != nil {
		t.Fatalf("metrics failed: %v", err)
	}
}
