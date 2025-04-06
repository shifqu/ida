#!/bin/sh
set -e

if [ "$DJANGO_ENVIRONMENT" = "development" ]; then
    echo "Development environment detected, installing in editable mode..."
    pip install --editable .[dev]
fi

echo "Applying database migrations..."
manage migrate --noinput

if [ "$DJANGO_ENVIRONMENT" = "production" ]; then
  echo "Collecting static files for $DJANGO_ENVIRONMENT..."
  manage collectstatic --noinput
fi

# Run the main command
echo "Starting the application..."
if [ "$1" = "gunicorn" ]; then
  shift
  exec gunicorn \
    --bind "${GUNICORN_BIND_IP:-0.0.0.0}:${GUNICORN_BIND_PORT:-38080}" \
    --workers "${GUNICORN_WORKERS:-4}" \
    --access-logfile "${GUNICORN_ACCESS_LOGFILE:-/log_data/access.log}" \
    --error-logfile "${GUNICORN_ERROR_LOGFILE:-/log_data/error.log}" \
    --log-level "${GUNICORN_LOG_LEVEL:-info}" \
    "$@"
else
  # Else, run whatever was passed (e.g. manage.py commands)
  exec "$@"
fi
