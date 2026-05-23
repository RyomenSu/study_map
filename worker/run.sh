#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting worker..."
exec python -m app.main
