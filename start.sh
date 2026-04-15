#!/bin/bash

set -e

echo "Starting backend..."

required_vars=(
  "SECRET_KEY"
  "ALGORITHM"
  "ACCESS_TOKEN_EXPIRE_MINUTES"
  "DATABASE_URL"
  "OPENAI_API_KEY"
)

for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: Missing environment variable: $var"
    exit 1
  fi
done

echo "Environment variables validated"

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000
