# Use uv for fast Python dependency management
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Copy dependency definition and lockfile for reproducible builds
COPY pyproject.toml uv.lock ./

# Install dependencies using uv sync (reads from pyproject.toml + uv.lock)
# --no-dev: Skip development dependencies
# --frozen: Use exact versions from uv.lock (production build)
RUN uv sync --no-dev --frozen

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
