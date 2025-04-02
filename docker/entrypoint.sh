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

echo "Compiling messages..."
manage compilemessages

# Run the main command
exec "$@"
