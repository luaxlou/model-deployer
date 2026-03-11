package ops

import (
	"context"

	"model-deploy-platform/internal/provider"
)

type Service struct {
	provider provider.Provider
}

func NewService(p provider.Provider) *Service { return &Service{provider: p} }

func (s *Service) QueryMetrics(ctx context.Context, deploymentID string) (provider.MetricsResponse, error) {
	return s.provider.GetMetrics(ctx, provider.MetricsQuery{DeploymentID: deploymentID})
}

func (s *Service) QueryLogs(ctx context.Context, deploymentID string) ([]string, error) {
	return s.provider.GetLogs(ctx, deploymentID)
}

func (s *Service) QueryCost(ctx context.Context, deploymentID, groupBy string) (CostGrouped, error) {
	resp, err := s.provider.EstimateCost(ctx, provider.CostQuery{DeploymentID: deploymentID, GroupBy: groupBy})
	if err != nil {
		return CostGrouped{}, err
	}
	return CostGrouped{GroupBy: groupBy, TotalUSD: resp.TotalUSD}, nil
}
