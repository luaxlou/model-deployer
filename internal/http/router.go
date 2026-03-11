package http

import (
	"encoding/json"
	"net/http"

	"model-deploy-platform/internal/http/handlers"
	"model-deploy-platform/internal/provider/eas"
	"model-deploy-platform/internal/service/deployment"
	"model-deploy-platform/internal/service/operation"
	"model-deploy-platform/internal/service/ops"
)

func NewRouter() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	p := eas.NewAdapter()
	deploySvc := deployment.NewService(p, operation.NewStore())
	opsSvc := ops.NewService(p)

	deployHandler := handlers.DeploymentHandler{Svc: deploySvc}
	debugHandler := handlers.DebugHandler{}
	opsHandler := handlers.OpsHandler{Svc: opsSvc}

	mux.HandleFunc("POST /deployments", deployHandler.Create)
	mux.HandleFunc("POST /debug/sessions/{id}/invoke", debugHandler.Invoke)
	mux.HandleFunc("GET /ops/costs", opsHandler.Cost)

	return mux
}
