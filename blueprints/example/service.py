from fastapi import FastAPI
from pydantic import BaseModel

from model.model import TinySklearnModel

app = FastAPI()
model = TinySklearnModel()


class PredictRequest(BaseModel):
    x1: float
    x2: float


@app.get('/healthz')
def healthz():
    return {'status': 'ok'}


@app.post('/predict')
def predict(req: PredictRequest):
    return model.predict(req.x1, req.x2)
