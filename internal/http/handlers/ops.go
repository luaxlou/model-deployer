package handlers

import (
	"encoding/json"
	"net/http"

	"model-deploy-platform/internal/service/ops"
)

type OpsHandler struct {
	Svc *ops.Service
}

func (h OpsHandler) Cost(w http.ResponseWriter, r *http.Request) {
	dep := r.URL.Query().Get("deploymentId")
	group := r.URL.Query().Get("groupBy")
	if group == "" {
		group = "deployment"
	}
	resp, err := h.Svc.QueryCost(r.Context(), dep, group)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(resp)
}
