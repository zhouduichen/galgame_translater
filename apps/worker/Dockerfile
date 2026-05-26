FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY packages/project-model ./packages/project-model
COPY packages/prompt-templates ./packages/prompt-templates
RUN pip install --no-cache-dir ./packages/project-model ./packages/prompt-templates

COPY apps/worker ./apps/worker
RUN pip install --no-cache-dir httpx python-dotenv

ENV PYTHONPATH=/app/apps/worker/src

CMD ["python", "-u", "-m", "worker.main"]
