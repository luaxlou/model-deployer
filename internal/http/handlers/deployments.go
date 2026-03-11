package handlers

import (
	"encoding/json"
	"net/http"

	"model-deploy-platform/internal/service/deployment"
)

type DeploymentHandler struct {
	Svc *deployment.Service
}

func (h DeploymentHandler) Create(w http.ResponseWriter, r *http.Request) {
	var req struct {
		DeploymentID string `json:"deploymentId"`
		Revision     string `json:"revision"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	resp, err := h.Svc.CreateDeployment(r.Context(), deployment.CreateRequest{DeploymentID: req.DeploymentID, Revision: req.Revision})
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(resp)
}
