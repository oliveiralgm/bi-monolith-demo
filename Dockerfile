FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BI_DEMO_PUBLIC=1 \
    PORT=8050

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8050

CMD gunicorn app:server --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120
