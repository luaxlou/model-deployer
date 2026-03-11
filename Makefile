.PHONY: test run fmt vet

test:
	go test ./... -v

run:
	go run ./cmd/controlplane

fmt:
	gofmt -w $(shell find . -name '*.go')

vet:
	go vet ./...
