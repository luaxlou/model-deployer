package image

import "fmt"

type Stage string

const (
	StageDraft    Stage = "draft"
	StageBuilt    Stage = "built"
	StageScanned  Stage = "scanned"
	StagePromoted Stage = "promoted"
)

type Item struct {
	Name     string
	Stage    Stage
	ScanPass bool
}

type Service struct {
	items map[string]Item
}

func NewService() *Service { return &Service{items: map[string]Item{}} }

func (s *Service) Create(name string) {
	s.items[name] = Item{Name: name, Stage: StageDraft}
}

func (s *Service) MarkBuilt(name string) {
	i := s.items[name]
	i.Stage = StageBuilt
	s.items[name] = i
}

func (s *Service) MarkScanned(name string, pass bool) {
	i := s.items[name]
	i.Stage = StageScanned
	i.ScanPass = pass
	s.items[name] = i
}

func (s *Service) Promote(name string) error {
	i := s.items[name]
	if i.Stage != StageScanned || !i.ScanPass {
		return fmt.Errorf("scan pass required")
	}
	i.Stage = StagePromoted
	s.items[name] = i
	return nil
}
