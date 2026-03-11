package spec

import "testing"

func TestDeploymentSpecValidation(t *testing.T) {
	invalid := DeploymentSpec{}
	if err := ValidateDeploymentSpec(invalid); err == nil {
		t.Fatal("expected error for missing required fields")
	}

	valid := DeploymentSpec{
		BaseImage: BaseImage{Digest: "sha256:abc"},
		RuntimePack: RuntimePack{RequirementsLock: "hash"},
		ModelArtifact: ModelArtifact{ArtifactVersion: "1.0.0"},
		WeightAsset: WeightAsset{Checksum: "sha256:def"},
		ComputeProfile: ComputeProfile{Provider: "eas"},
	}
	if err := ValidateDeploymentSpec(valid); err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}
