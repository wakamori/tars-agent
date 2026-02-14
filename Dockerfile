# Use uv for fast Python dependency management
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Install dependencies using uv
# NOTE: Dependencies are explicitly listed here for Docker build reliability.
# Keep in sync with pyproject.toml [project.dependencies]
# When updating dependencies, update both files:
#   1. pyproject.toml (for local dev with uv sync)
#   2. Dockerfile (for production builds)
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv \
    fastapi==0.115.0 \
    uvicorn[standard]==0.32.0 \
    python-multipart==0.0.12 \
    google-cloud-aiplatform==1.71.0 \
    pydantic==2.9.2

# Final runtime image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8080

# Run the application from backend directory
WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
