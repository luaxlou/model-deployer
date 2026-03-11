from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression


def main() -> None:
    rng = np.random.default_rng(42)
    x = rng.normal(size=(256, 2))
    y = (0.8 * x[:, 0] - 0.4 * x[:, 1] + 0.1 > 0).astype(int)

    model = LogisticRegression(max_iter=200)
    model.fit(x, y)

    out = Path(__file__).with_name("tiny_model.joblib")
    joblib.dump(model, out)
    print(f"saved model to {out}")


if __name__ == "__main__":
    main()
