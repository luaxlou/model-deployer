from __future__ import annotations

import math


class TinyLinearModel:
    """A tiny, deterministic model for local deployment smoke testing."""

    def __init__(self) -> None:
        self.w1 = 0.8
        self.w2 = -0.4
        self.bias = 0.1

    def predict(self, x1: float, x2: float) -> dict:
        score = self.w1 * x1 + self.w2 * x2 + self.bias
        prob = 1.0 / (1.0 + math.exp(-score))
        label = 1 if prob >= 0.5 else 0
        return {"label": label, "score": score, "probability": prob}
