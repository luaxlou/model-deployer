package handlers

import (
	"encoding/json"
	"net/http"
)

type DebugHandler struct{}

func (h DebugHandler) Invoke(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{"status": "invoked"})
}
