package deployment

import (
	"context"
	"fmt"
	"sync/atomic"

	"model-deploy-platform/internal/provider"
	"model-deploy-platform/internal/service/operation"
)

type Service struct {
	provider provider.Provider
	ops      *operation.Store
	counter  uint64
}

type CreateRequest struct {
	DeploymentID string
	Revision     string
}

type CreateResponse struct {
	OperationID string `json:"operationId"`
	Status      string `json:"status"`
}

func NewService(p provider.Provider, ops *operation.Store) *Service {
	return &Service{provider: p, ops: ops}
}

func (s *Service) CreateDeployment(ctx context.Context, req CreateRequest) (CreateResponse, error) {
	opID := fmt.Sprintf("op-%d", atomic.AddUint64(&s.counter, 1))
	s.ops.Save(operation.Operation{ID: opID, Status: operation.StatusPending})
	if _, err := s.provider.Deploy(ctx, provider.DeployRequest{DeploymentID: req.DeploymentID, Revision: req.Revision}); err != nil {
		return CreateResponse{}, err
	}
	return CreateResponse{OperationID: opID, Status: string(operation.StatusPending)}, nil
}
