# Stage 1: Base build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install gettext because it is required for django's compilemessages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements files first for better caching
COPY requirements/ /app/requirements/

# Upgrade pip, install pip-tools, and install Python dependencies
RUN pip install --upgrade pip pip-tools && \
    pip-sync requirements/main.txt

# Set up entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Stage 2: Development stage
FROM builder AS development

# Install development dependencies
RUN pip-sync requirements/dev.txt

# Run the application
CMD ["manage", "runserver", "0.0.0.0:38080"]

# Stage 3: Production stage
FROM builder AS production

# Create a non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

WORKDIR /app

# Create directories with proper permissions
RUN mkdir -p /db_data /static_data /media_data /log_data && \
    chown -R appuser:appuser /db_data /static_data /media_data /log_data /app

# Copy application code
COPY --chown=appuser:appuser src/ src/
COPY --chown=appuser:appuser pyproject.toml pyproject.toml

# Install the application
RUN pip install .

# Switch to non-root user
USER appuser

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:38080", "--workers", "4", "ida.wsgi:application"]
