package spec

type BaseImage struct {
	Name          string
	CUDA          string
	Python        string
	OS            string
	SecurityLevel string
	Digest        string
}

type RuntimePack struct {
	RequirementsLock string
	StartupCmd       string
	HealthCheck      string
	EnvSchema        map[string]string
}

type ModelArtifact struct {
	ModelName       string
	TaskType        string
	Entrypoint      string
	Framework       string
	ArtifactVersion string
}

type WeightAsset struct {
	URI        string
	Checksum   string
	Size       int64
	License    string
	Encryption string
}

type ComputeProfile struct {
	Provider    string
	InstanceType string
	GPU         int
	CPU         int
	MemoryGB    int
	Autoscaling bool
	SpotPolicy  string
}

type DeploymentSpec struct {
	BaseImage      BaseImage
	RuntimePack    RuntimePack
	ModelArtifact  ModelArtifact
	WeightAsset    WeightAsset
	ComputeProfile ComputeProfile
	Stage          string
	BudgetLimit    float64
}
