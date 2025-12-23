# Repository Intelligence Scanner - Enterprise Deployment
# Multi-stage build for optimized production image

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash scanner

# Set work directory
WORKDIR /app

# Install Python dependencies in stages for better caching
FROM base as dependencies

# Copy dependency files
COPY pyproject.toml ./

# Install core dependencies
RUN pip install --no-cache-dir setuptools wheel

# Install the package itself with API dependencies
RUN pip install --no-cache-dir -e ".[api]" .

# Optional AI dependencies stage
FROM dependencies as ai-dependencies

# Install AI/ML dependencies (optional but recommended for full functionality)
RUN pip install --no-cache-dir \
    transformers \
    torch \
    llama-cpp-python

# Production stage
FROM ai-dependencies as production

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/models && \
    chown -R scanner:scanner /app

# Switch to non-root user
USER scanner

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.core.pipeline.analysis; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "src.cli", "--help"]</content>
<parameter name="filePath">/home/dee/workspace/AI/Repo-Scanner/Dockerfile