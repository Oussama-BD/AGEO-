FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements.lock.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY . .
RUN mkdir -p data/raw data/processed reports
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
