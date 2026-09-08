FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY static/ ./static/
COPY migrations/ ./migrations/
COPY migrate.py .
WORKDIR /app/src
CMD ["sh", "-c", "python ../migrate.py && uvicorn main:app --host 0.0.0.0 --port 8000"]
