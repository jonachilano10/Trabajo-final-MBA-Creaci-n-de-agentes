FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AGENT_DATA_DIR=/app/runtime

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/runtime/data /app/runtime/salidas /app/runtime/corridas

EXPOSE 8000
VOLUME ["/app/runtime"]
CMD ["python", "run_web.py", "--host", "0.0.0.0"]
