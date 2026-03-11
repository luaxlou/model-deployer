package main

import (
	"log"
	"net/http"

	httpapi "model-deploy-platform/internal/http"
)

func main() {
	r := httpapi.NewRouter()
	log.Println("control-plane listening on :8080")
	if err := http.ListenAndServe(":8080", r); err != nil {
		log.Fatal(err)
	}
}
