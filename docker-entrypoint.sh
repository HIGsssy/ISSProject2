#!/bin/bash
set -e

#!/bin/bash
set -e

# Check if this is first run
if [ ! -f "/app/.env" ] || [ ! -s "/app/.env" ]; then
    echo "=============================================================================="
    echo "ISS Portal - First Run Setup"
    echo "=============================================================================="
    echo ""
    echo "Starting web-based setup wizard..."
    echo ""
    
    # Run web setup wizard
    python /app/setup_wizard.py
    
    echo ""
    echo "✓ Setup complete! Continuing with application startup..."
    echo ""
fi

echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U iss_user > /dev/null 2>&1; do
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
