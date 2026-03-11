package provider

import "context"

type BuildImageRequest struct {
	Name   string
	Digest string
}

type BuildImageResponse struct {
	ImageRef string
}

type DeployRequest struct {
	DeploymentID string
	Revision     string
}

type DeployResponse struct {
	ProviderID string
	Status     string
}

type ScaleRequest struct {
	DeploymentID string
	Replicas     int
}

type RollbackRequest struct {
	DeploymentID string
	ToRevision   string
}

type MetricsQuery struct {
	DeploymentID string
}

type MetricsResponse struct {
	QPS     float64
	P95MS   float64
	ErrRate float64
}

type CostQuery struct {
	DeploymentID string
	GroupBy      string
}

type CostResponse struct {
	TotalUSD float64
}

type Provider interface {
	BuildImage(ctx context.Context, req BuildImageRequest) (BuildImageResponse, error)
	Deploy(ctx context.Context, req DeployRequest) (DeployResponse, error)
	Scale(ctx context.Context, req ScaleRequest) error
	Rollback(ctx context.Context, req RollbackRequest) error
	GetLogs(ctx context.Context, deploymentID string) ([]string, error)
	GetMetrics(ctx context.Context, req MetricsQuery) (MetricsResponse, error)
	EstimateCost(ctx context.Context, req CostQuery) (CostResponse, error)
}
