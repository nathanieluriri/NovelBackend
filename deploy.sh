#!/bin/bash

set -e  # Exit on error

echo "🔍 Validating .env file..."

# Ensure .env file exists
if [ ! -f .env ]; then
  echo "❌ .env file not found!"
  exit 1
fi

# Ensure .env.example file exists
if [ ! -f .env.example ]; then
  echo "❌ .env.example file not found!"
  exit 1
fi

# Get required and actual keys
REQUIRED_KEYS=$(grep -v '^#' .env.example | cut -d= -f1 | sort)
ACTUAL_KEYS=$(grep -v '^#' .env | cut -d= -f1 | sort)

# Find missing keys
MISSING_KEYS=$(comm -23 <(echo "$REQUIRED_KEYS") <(echo "$ACTUAL_KEYS"))

if [ -n "$MISSING_KEYS" ]; then
  echo "❌ Missing required environment variables in .env:"
  echo "$MISSING_KEYS"
  exit 1
fi

# Check for empty values
echo "$REQUIRED_KEYS" | while IFS= read -r key; do
  val=$(grep "^$key=" .env | cut -d '=' -f2-)
  if [ -z "$val" ]; then
    echo "❌ Environment variable '$key' is defined but empty!"
    exit 1
  fi
done

echo "✅ .env validation passed!"

echo "🔄 Pulling latest code..."
git pull origin master

echo "🛠️ Building Docker images..."
docker compose build

echo "🚀 Restarting services..."
docker compose up -d

echo "✅ Deployment complete!"
