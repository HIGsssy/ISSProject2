#!/bin/bash
# ISS Portal - Stop Script
# Stops the ISS Portal application (keeps data intact)

cd "$(dirname "$0")"

echo "Stopping ISS Portal..."
docker-compose stop

echo ""
echo "ISS Portal stopped."
echo ""
echo "To start again: ./start.sh or docker-compose up -d"
echo "To view status: ./status.sh or docker-compose ps"
