#!/bin/sh
set -e

echo "Applying database migrations..."
manage migrate --noinput

if [ "$DJANGO_ENVIRONMENT" = "production" ]; then
  echo "Collecting static files for $DJANGO_ENVIRONMENT..."
  manage collectstatic --noinput
fi

echo "Compiling messages..."
manage compilemessages || true  # Ignore errors

# Run the main command
exec "$@"
