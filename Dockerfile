# Stage 1: Base build stage
FROM python:3.13-alpine AS builder

WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install gettext because it is required for django's compilemessages
# Install git because django-telegram-app is currently installed from a git repository
RUN apk add --no-cache gettext git

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
    -D \
    -H \
    -s "/sbin/nologin" \
    -u "${UID}" \
    appuser

WORKDIR /app

# Create directories with proper permissions
RUN mkdir -p /db_data /static_data /media_data /log_data && \
    chown -R appuser:appuser /db_data /static_data /media_data /log_data /app

# Copy application code
COPY --chown=appuser:appuser src/ src/
COPY --chown=appuser:appuser pyproject.toml pyproject.toml

# Compile translations
RUN cd src/apps && django-admin compilemessages

# Install the application
RUN pip install .

# Switch to non-root user
USER appuser

# Run the application with Gunicorn
CMD ["gunicorn", "ida.wsgi:application"]
