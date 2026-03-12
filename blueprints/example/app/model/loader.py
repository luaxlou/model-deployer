from __future__ import annotations

from pathlib import Path

import joblib


def load_sklearn_model(model_path: str | None = None):
    path = Path(model_path) if model_path else Path(__file__).with_name('tiny_model.joblib')
    return joblib.load(path)
