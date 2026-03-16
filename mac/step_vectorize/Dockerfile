FROM python:3.11-slim

WORKDIR /app

COPY step_vectorize/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY shared /app/shared
COPY step_vectorize/main.py /app/main.py

ENV PYTHONPATH=/app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
