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

# Change to backend directory for proper module resolution
cd /app

# Start the application with proper error handling
echo "Starting uvicorn server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port "$PORT" --access-log
