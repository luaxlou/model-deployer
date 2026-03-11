package eas

import (
	"context"
	"fmt"

	"model-deploy-platform/internal/provider"
)

type Adapter struct{}

func NewAdapter() *Adapter { return &Adapter{} }

func (a *Adapter) BuildImage(_ context.Context, req provider.BuildImageRequest) (provider.BuildImageResponse, error) {
	return provider.BuildImageResponse{ImageRef: fmt.Sprintf("acr.local/%s@%s", req.Name, req.Digest)}, nil
}

func (a *Adapter) Deploy(_ context.Context, req provider.DeployRequest) (provider.DeployResponse, error) {
	return provider.DeployResponse{ProviderID: "eas-" + req.DeploymentID, Status: "pending"}, nil
}

func (a *Adapter) Scale(_ context.Context, _ provider.ScaleRequest) error { return nil }

func (a *Adapter) Rollback(_ context.Context, _ provider.RollbackRequest) error { return nil }

func (a *Adapter) GetLogs(_ context.Context, deploymentID string) ([]string, error) {
	return []string{"log for " + deploymentID}, nil
}

func (a *Adapter) GetMetrics(_ context.Context, _ provider.MetricsQuery) (provider.MetricsResponse, error) {
	return provider.MetricsResponse{QPS: 12.5, P95MS: 120, ErrRate: 0.01}, nil
}

func (a *Adapter) EstimateCost(_ context.Context, _ provider.CostQuery) (provider.CostResponse, error) {
	return provider.CostResponse{TotalUSD: 3.14}, nil
}
