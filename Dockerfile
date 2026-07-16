FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .
COPY docs/ /docs/

RUN mkdir -p /app/data/uploads/photos /app/data/uploads/verification \
    && chown -R appuser:appuser /app/data/uploads

EXPOSE 8000

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

USER appuser

ENTRYPOINT ["./entrypoint.sh"]
