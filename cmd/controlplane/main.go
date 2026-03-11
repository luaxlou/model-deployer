package main

import (
	"fmt"
	"log"
	"net/http"

	"github.com/luaxlou/glow/starter/glowconfig"
	httpapi "model-deploy-platform/internal/http"
)

func main() {
	port := glowconfig.GetInt("server.port")
	if port == 0 {
		port = 8080
	}

	addr := fmt.Sprintf(":%d", port)
	r := httpapi.NewRouter()

	log.Printf("control-plane listening on %s", addr)
	if err := http.ListenAndServe(addr, r); err != nil {
		log.Fatal(err)
	}
}
