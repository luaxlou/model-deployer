package ops

import (
	"context"
	"testing"

	"model-deploy-platform/internal/provider/eas"
)

func TestQueryCostGroupedByDeployment(t *testing.T) {
	svc := NewService(eas.NewAdapter())
	resp, err := svc.QueryCost(context.Background(), "dep-1", "deployment")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.GroupBy != "deployment" {
		t.Fatalf("expected deployment group, got %s", resp.GroupBy)
	}
	if resp.TotalUSD <= 0 {
		t.Fatalf("expected positive cost, got %f", resp.TotalUSD)
	}
}
