FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e . || pip install --no-cache-dir \
    fastapi "uvicorn[standard]" pydantic pydantic-settings pandas numpy \
    sqlalchemy alembic httpx celery redis
COPY . /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
