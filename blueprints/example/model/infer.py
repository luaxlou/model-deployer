from __future__ import annotations

from typing import Any

import numpy as np

from model.loader import load_sklearn_model


class TinySklearnModel:
    """A tiny trained sklearn model for local deployment experiments."""

    def __init__(self, model_path: str | None = None) -> None:
        self.model = load_sklearn_model(model_path)

    def predict(self, x1: float, x2: float) -> dict[str, Any]:
        features = np.array([[x1, x2]], dtype=float)
        proba = float(self.model.predict_proba(features)[0][1])
        label = int(proba >= 0.5)
        return {'label': label, 'probability': proba}
