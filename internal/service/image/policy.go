package image

func CanPromote(i Item) bool {
	return i.Stage == StageScanned && i.ScanPass
}
