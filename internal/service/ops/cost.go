package ops

type CostGrouped struct {
	GroupBy  string  `json:"groupBy"`
	TotalUSD float64 `json:"totalUsd"`
}
