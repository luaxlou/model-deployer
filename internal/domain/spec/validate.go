package spec

import "fmt"

func ValidateDeploymentSpec(s DeploymentSpec) error {
	if s.BaseImage.Digest == "" {
		return fmt.Errorf("baseImage.digest is required")
	}
	if s.RuntimePack.RequirementsLock == "" {
		return fmt.Errorf("runtimePack.requirementsLock is required")
	}
	if s.ModelArtifact.ArtifactVersion == "" {
		return fmt.Errorf("modelArtifact.artifactVersion is required")
	}
	if s.WeightAsset.Checksum == "" {
		return fmt.Errorf("weightAsset.checksum is required")
	}
	if s.ComputeProfile.Provider == "" {
		return fmt.Errorf("computeProfile.provider is required")
	}
	return nil
}
