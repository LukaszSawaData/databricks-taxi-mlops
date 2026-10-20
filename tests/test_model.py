import numpy as np
import pandas as pd
import pytest

from taxi_mlops.model import (
    FEATURES,
    REQUEST_COLUMNS,
    TARGET,
    ZIP_FEATURES,
    FarePredictor,
    build_model,
    evaluate,
    promotion_decision,
    psi,
    split,
)

ZIPS = [10001, 10002, 10003]


@pytest.fixture
def zip_features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pickup_zip": ZIPS,
            "zip_trip_count": [100, 50, 10],
            "zip_avg_fare": [10.0, 15.0, 30.0],
            "zip_avg_fare_per_mile": [3.0, 4.0, 6.0],
        }
    )


@pytest.fixture
def training_set(zip_features) -> pd.DataFrame:
    """Shape of FeatureEngineeringClient.create_training_set(...).load_df()."""
    rng = np.random.default_rng(0)
    n = 600
    df = pd.DataFrame(
        {
            "trip_distance": rng.uniform(0.2, 20, n),
            "pickup_hour": rng.integers(0, 24, n),
            "pickup_dow": rng.integers(1, 8, n),
            "pickup_zip": rng.choice(ZIPS, n),
        }
    ).merge(zip_features, on="pickup_zip")
    df[TARGET] = 2.5 + df["zip_avg_fare_per_mile"] * df["trip_distance"] + rng.normal(0, 1, n)
    return df


def test_split_uses_feature_columns_and_is_deterministic(training_set):
    X1, X_test, _, _ = split(training_set)
    X1b, _, _, _ = split(training_set)
    assert list(X1.columns) == FEATURES
    assert X1.index.equals(X1b.index)
    assert len(X_test) == int(len(training_set) * 0.2)


def test_predictor_learns_and_uses_zip_features(training_set, zip_features):
    X_train, X_test, y_train, y_test = split(training_set)
    predictor = FarePredictor(build_model().fit(X_train, y_train), zip_features)
    # Request has raw columns only; the predictor adds the zip features itself.
    request = training_set.loc[X_test.index, REQUEST_COLUMNS]
    metrics = evaluate(predictor, request, y_test)
    assert metrics["rmse"] < 3.0
    assert metrics["r2"] > 0.9


def test_unknown_zip_gets_defaults_not_nan(zip_features):
    predictor = FarePredictor(model=None, zip_features=zip_features)
    request = pd.DataFrame(
        [{"trip_distance": 2.0, "pickup_hour": 1, "pickup_dow": 3, "pickup_zip": 1}]
    )
    X = predictor.add_zip_features(request)
    assert list(X.columns) == FEATURES
    assert not X[ZIP_FEATURES].isna().any().any()
    assert X.loc[0, "zip_avg_fare"] == pytest.approx(zip_features["zip_avg_fare"].mean())


def test_predictor_drops_dataframe_attrs(zip_features):
    """Regression: Spark toPandas() attrs (pyspark objects) must not end up in the pickle."""
    import pickle

    class SparkOnly:  # stands in for pyspark.sql.metrics.PlanMetrics
        pass

    zip_features.attrs["metrics"] = SparkOnly()
    blob = pickle.dumps(FarePredictor(model=None, zip_features=zip_features))
    assert b"SparkOnly" not in blob


@pytest.mark.parametrize(
    ("candidate", "champion", "promote"),
    [
        (3.0, None, True),  # first model
        (3.0, 3.5, True),  # better
        (3.5, 3.5, True),  # equal (deterministic retrain)
        (4.0, 3.5, False),  # worse -> keep champion
        (9.0, None, False),  # over absolute threshold
        (float("nan"), 3.0, False),
    ],
)
def test_promotion_decision(candidate, champion, promote):
    assert promotion_decision(candidate, champion, max_rmse=6.0)[0] is promote


def test_tolerance_allows_small_regression():
    assert promotion_decision(3.6, 3.5, max_rmse=6.0, tolerance=0.05)[0] is True


def test_psi_detects_shift():
    rng = np.random.default_rng(1)
    base = pd.Series(rng.normal(3, 1, 5000))
    assert psi(base, pd.Series(rng.normal(3, 1, 5000))) < 0.1
    assert psi(base, pd.Series(rng.normal(5, 1, 5000))) > 0.2
