package handlers_test

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"testing"

	httpapi "model-deploy-platform/internal/http"
)

func TestCreateDeploymentEndpoint(t *testing.T) {
	r := httpapi.NewRouter()
	body := []byte(`{"deploymentId":"dep-1","revision":"r1"}`)
	req := httptest.NewRequest(http.MethodPost, "/deployments", bytes.NewReader(body))
	rw := httptest.NewRecorder()
	r.ServeHTTP(rw, req)
	if rw.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rw.Code)
	}
}

func TestDebugSessionInvokeEndpoint(t *testing.T) {
	r := httpapi.NewRouter()
	req := httptest.NewRequest(http.MethodPost, "/debug/sessions/abc/invoke", nil)
	rw := httptest.NewRecorder()
	r.ServeHTTP(rw, req)
	if rw.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rw.Code)
	}
}

func TestOpsCostQueryEndpoint(t *testing.T) {
	r := httpapi.NewRouter()
	req := httptest.NewRequest(http.MethodGet, "/ops/costs?deploymentId=dep-1&groupBy=deployment", nil)
	rw := httptest.NewRecorder()
	r.ServeHTTP(rw, req)
	if rw.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rw.Code)
	}
}
