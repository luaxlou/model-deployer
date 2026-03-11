from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np


class TinySklearnModel:
    """A tiny trained sklearn model for local deployment experiments."""

    def __init__(self, model_path: str | None = None) -> None:
        path = Path(model_path) if model_path else Path(__file__).with_name("tiny_model.joblib")
        self.model = joblib.load(path)

    def predict(self, x1: float, x2: float) -> dict[str, Any]:
        features = np.array([[x1, x2]], dtype=float)
        proba = float(self.model.predict_proba(features)[0][1])
        label = int(proba >= 0.5)
        return {"label": label, "probability": proba}
