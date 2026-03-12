from pydantic import BaseModel


class PredictRequest(BaseModel):
    x1: float
    x2: float
