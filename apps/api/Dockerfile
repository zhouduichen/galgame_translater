FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY packages/project-model ./packages/project-model
COPY packages/prompt-templates ./packages/prompt-templates
RUN pip install --no-cache-dir ./packages/project-model ./packages/prompt-templates

COPY apps/api ./apps/api
RUN pip install --no-cache-dir uvicorn fastapi sqlalchemy python-multipart

ENV PYTHONPATH=/app/apps/api/src

EXPOSE 8001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
