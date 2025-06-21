#!/bin/bash
set -e

# Set default port if not provided
export PORT=${PORT:-8000}

echo "Starting Document AI on port $PORT"
echo "Environment: ${RAILWAY_ENVIRONMENT:-local}"

# Validate port is numeric
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "Error: PORT must be a number, got: $PORT"
    exit 1
fi

# Add the backend directory to Python path for app module resolution
export PYTHONPATH="/app/backend:$PYTHONPATH"

# Change to backend directory for proper module resolution
cd /app/backend

echo "Python path: $PYTHONPATH"
echo "Working directory: $(pwd)"
echo "Starting uvicorn server..."

# Start the application with proper error handling
exec uvicorn main:app --host 0.0.0.0 --port "$PORT" --access-log
