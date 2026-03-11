package mcp

type Server struct {
	Tools Tools
}

func NewServer(tools Tools) *Server {
	return &Server{Tools: tools}
}
