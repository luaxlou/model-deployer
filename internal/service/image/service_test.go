package image

import "testing"

func TestPromoteImageRequiresScanPass(t *testing.T) {
	svc := NewService()
	svc.Create("img")
	svc.MarkBuilt("img")
	svc.MarkScanned("img", false)
	if err := svc.Promote("img"); err == nil {
		t.Fatal("expected error when scan not pass")
	}

	svc.MarkScanned("img", true)
	if err := svc.Promote("img"); err != nil {
		t.Fatalf("expected success, got %v", err)
	}
}
