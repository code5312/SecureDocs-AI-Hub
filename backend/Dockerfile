FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /workspace/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app backend/app ./app
COPY --chown=app:app backend/alembic.ini ./alembic.ini
COPY --chown=app:app backend/alembic ./alembic

FROM base AS test
USER root
COPY --chown=app:app backend/tests ./tests
COPY --chown=app:app backend/pytest.ini ./pytest.ini
COPY --chown=app:app backend/Dockerfile ./Dockerfile
COPY --chown=app:app docker-compose.yml /workspace/docker-compose.yml
COPY --chown=app:app scripts /workspace/scripts
COPY --chown=app:app nginx /workspace/nginx
USER app
CMD ["python", "-m", "pytest", "-v"]

FROM base AS runtime
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
