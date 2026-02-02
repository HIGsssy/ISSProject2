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
while ! pg_isready -h db -p 5432 -U ${POSTGRES_USER:-iss_user} > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready!"

# If this was first run, create database user with the password from .env
if [ -f "/app/.env.firstrun" ]; then
    echo "Initializing database user..."
    
    # Source the .env file to get the password
    source /app/.env
    
    # Create user and database using postgres superuser
    PGPASSWORD=${POSTGRES_PASSWORD:-change-this-password} psql -h db -U postgres -tc "SELECT 1 FROM pg_user WHERE usename = '${POSTGRES_USER}'" | grep -q 1 || \
    PGPASSWORD=${POSTGRES_PASSWORD:-change-this-password} psql -h db -U postgres <<-EOSQL
        CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';
        CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};
        GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};
EOSQL
    
    echo "✓ Database user created"
    rm /app/.env.firstrun
fi

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Creating initial data..."
python manage.py create_initial_data || true

echo "Starting application..."
exec "$@"
