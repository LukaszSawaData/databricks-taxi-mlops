"""Pure model logic: pandas + scikit-learn only (no Spark, MLflow or I/O). Unit-tested locally."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# What a client sends to the endpoint.
REQUEST_COLUMNS = ["trip_distance", "pickup_hour", "pickup_dow", "pickup_zip"]
# What the Feature Store table `pickup_zip_features` adds (lookup key: pickup_zip).
ZIP_KEY = "pickup_zip"
ZIP_FEATURES = ["zip_trip_count", "zip_avg_fare", "zip_avg_fare_per_mile"]
FEATURES = REQUEST_COLUMNS + ZIP_FEATURES
TARGET = "fare_amount"
CHAMPION_ALIAS = "champion"


def build_model(seed: int = 42) -> HistGradientBoostingRegressor:
    # Small and fast on purpose: the project is about MLOps, not accuracy.
    return HistGradientBoostingRegressor(max_iter=100, learning_rate=0.1, random_state=seed)


def split(df: pd.DataFrame, test_size: float = 0.2, seed: int = 42):
    X = df[FEATURES].astype("float64")
    y = df[TARGET].astype("float64")
    return train_test_split(X, y, test_size=test_size, random_state=seed)


def evaluate(model, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
    pred = np.asarray(model.predict(X), dtype="float64")
    return {
        "rmse": float(np.sqrt(mean_squared_error(y, pred))),
        "mae": float(mean_absolute_error(y, pred)),
        "r2": float(r2_score(y, pred)),
    }


class FarePredictor:
    """sklearn model + a snapshot of the zip features taken at training time.

    Free Edition has no online feature store, so real-time serving cannot look features up.
    The zip table is tiny (a few hundred rows), so it travels inside the model artifact.
    """

    def __init__(self, model, zip_features: pd.DataFrame):
        zf = zip_features[[ZIP_KEY] + ZIP_FEATURES].astype("float64")
        self.model = model
        self.zip_table = zf.set_index(ZIP_KEY)
        # Unknown zip at inference time -> global average instead of NaN.
        self.defaults = zf[ZIP_FEATURES].mean().to_dict()

    def add_zip_features(self, request: pd.DataFrame) -> pd.DataFrame:
        X = request[REQUEST_COLUMNS].astype("float64").reset_index(drop=True)
        joined = X.join(self.zip_table, on=ZIP_KEY)
        return joined.fillna(self.defaults)[FEATURES]

    def predict(self, request: pd.DataFrame) -> np.ndarray:
        return self.model.predict(self.add_zip_features(request))


def promotion_decision(
    candidate_rmse: float,
    champion_rmse: float | None,
    max_rmse: float,
    tolerance: float = 0.0,
) -> tuple[bool, str]:
    """Returns (promote, reason). Used by the deployment job's evaluation task."""
    if not np.isfinite(candidate_rmse) or candidate_rmse > max_rmse:
        return False, f"candidate rmse {candidate_rmse:.3f} > max_rmse {max_rmse:.3f}"
    if champion_rmse is None:
        return True, "no champion yet"
    if candidate_rmse <= champion_rmse * (1 + tolerance):
        return True, f"candidate {candidate_rmse:.3f} <= champion {champion_rmse:.3f}"
    return False, f"candidate {candidate_rmse:.3f} worse than champion {champion_rmse:.3f}"


def psi(expected: pd.Series, actual: pd.Series, bins: int = 10) -> float:
    """Population Stability Index. < 0.1 stable, 0.1-0.2 moderate, > 0.2 drift."""
    expected, actual = expected.dropna().astype(float), actual.dropna().astype(float)
    if expected.empty or actual.empty:
        return float("nan")
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.histogram(expected, edges)[0] / len(expected)
    a = np.histogram(actual, edges)[0] / len(actual)
    e, a = np.clip(e, 1e-6, None), np.clip(a, 1e-6, None)
    return float(np.sum((a - e) * np.log(a / e)))
