from fastapi import FastAPI

from app.model.infer import TinySklearnModel
from app.service.schemas import PredictRequest

app = FastAPI()
model = TinySklearnModel()


@app.get('/healthz')
def healthz():
    return {'status': 'ok'}


@app.post('/predict')
def predict(req: PredictRequest):
    return model.predict(req.x1, req.x2)
