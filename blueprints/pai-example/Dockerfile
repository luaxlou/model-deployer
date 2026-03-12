FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY service/ /app/service/
COPY model/ /app/model/
COPY .mdp/weights/ /app/.mdp/weights/
CMD ["python", "-m", "uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "18080"]
