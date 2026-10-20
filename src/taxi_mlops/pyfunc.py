"""MLflow wrapper. Shipped with the model via code_paths, so serving can import taxi_mlops."""

import mlflow.pyfunc
import pandas as pd

from taxi_mlops.model import FarePredictor


class TaxiFareModel(mlflow.pyfunc.PythonModel):
    def __init__(self, predictor: FarePredictor):
        self.predictor = predictor

    def predict(self, context, model_input: pd.DataFrame, params=None):
        return self.predictor.predict(model_input)
