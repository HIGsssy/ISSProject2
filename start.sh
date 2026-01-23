#!/bin/bash
# ISS Portal - Start Script
# Starts the ISS Portal application

cd "$(dirname "$0")"

echo "Starting ISS Portal..."
docker-compose up -d

echo ""
echo "Waiting for services to start..."
sleep 3

echo ""
docker-compose ps

echo ""
echo "ISS Portal is starting..."
echo "Access at: http://localhost (or http://$(hostname -I | awk '{print $1}'))"
echo ""
echo "View logs: docker-compose logs -f web"
