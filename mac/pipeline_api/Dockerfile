FROM python:3.11-slim

WORKDIR /app

COPY pipeline_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY pipeline_api/main.py /app/main.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8011"]
