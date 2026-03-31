FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir httpx>=0.27 rich>=0.13

# Copy source
COPY src/ ./src/
COPY examples/ ./examples/

ENV PYTHONPATH=/app

CMD ["python", "-m", "src.main"]
