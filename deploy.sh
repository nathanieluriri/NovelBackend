#!/bin/bash

echo "🔄 Pulling latest code..."
git pull origin main

echo "🛠️ Building Docker images..."
docker compose build

echo "🚀 Restarting services..."
docker compose up -d

echo "✅ Deployment complete!"
