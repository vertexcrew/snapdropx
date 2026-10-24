FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8000

# Render / generic hosts inject $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn snapdropx.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
