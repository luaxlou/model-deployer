package operation

import "sync"

type Status string

const (
	StatusPending Status = "pending"
	StatusDone    Status = "done"
)

type Operation struct {
	ID     string
	Status Status
}

type Store struct {
	mu   sync.RWMutex
	data map[string]Operation
}

func NewStore() *Store {
	return &Store{data: map[string]Operation{}}
}

func (s *Store) Save(op Operation) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.data[op.ID] = op
}

func (s *Store) Get(id string) (Operation, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	op, ok := s.data[id]
	return op, ok
}
