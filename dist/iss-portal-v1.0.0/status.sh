#!/bin/bash
# ISS Portal - Status Script
# Shows current status of ISS Portal services

cd "$(dirname "$0")"

echo "========================================"
echo "ISS Portal - Service Status"
echo "========================================"
echo ""

# Container status
echo "Container Status:"
docker-compose ps
echo ""

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✓ Services are running"
    echo ""
    
    # Database status
    echo "Database Status:"
    if docker-compose exec -T db psql -U iss_user -d iss_portal_db -c "SELECT pg_size_pretty(pg_database_size('iss_portal_db')) as db_size;" 2>/dev/null; then
        echo ""
    else
        echo "⚠ Unable to query database"
        echo ""
    fi
    
    # Recent logs
    echo "Recent Application Logs (last 10 lines):"
    docker-compose logs --tail=10 web
    echo ""
    
    # Access information
    echo "========================================"
    echo "Access Information:"
    echo "========================================"
    echo "URL: http://localhost"
    echo "URL: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo 'your-server-ip')"
    echo ""
    echo "Commands:"
    echo "  View full logs: docker-compose logs -f web"
    echo "  Restart: docker-compose restart"
    echo "  Stop: ./stop.sh"
else
    echo "⚠ Services are not running"
    echo ""
    echo "Start services: ./start.sh or docker-compose up -d"
fi
echo ""
