#!/bin/sh
set -e

echo "Starting main-api..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
