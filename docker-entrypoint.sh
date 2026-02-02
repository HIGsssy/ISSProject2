#!/bin/bash
set -e

# Check if this is first run (no .env or minimal .env)
if [ ! -f "/app/.env" ] || [ ! -s "/app/.env" ] || ! grep -q "FIELD_ENCRYPTION_KEY=" /app/.env 2>/dev/null; then
    echo "=============================================================================="
    echo "First Time Setup Required"
    echo "=============================================================================="
    echo ""
    echo "No configuration found. Starting interactive setup..."
    echo ""
    
    # Run interactive setup
    python manage.py interactive_setup
    
    echo ""
    echo "Setup complete! Continuing with deployment..."
    echo ""
fi

echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U ${POSTGRES_USER:-iss_user} > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready!"

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Creating initial data..."
python manage.py create_initial_data || true

echo "Starting application..."
exec "$@"
