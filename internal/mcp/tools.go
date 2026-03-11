package mcp

import (
	"context"

	"model-deploy-platform/internal/service/deployment"
	"model-deploy-platform/internal/service/ops"
)

type Tools struct {
	Deployment *deployment.Service
	Ops        *ops.Service
}

func (t Tools) DeployCreate(ctx context.Context, deploymentID, revision string) (deployment.CreateResponse, error) {
	return t.Deployment.CreateDeployment(ctx, deployment.CreateRequest{DeploymentID: deploymentID, Revision: revision})
}

func (t Tools) QueryCost(ctx context.Context, deploymentID, groupBy string) (ops.CostGrouped, error) {
	return t.Ops.QueryCost(ctx, deploymentID, groupBy)
}
