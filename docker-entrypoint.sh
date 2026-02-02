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
    
    # Generate a temporary but valid Fernet key
    TEMP_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # Create minimal .env file to allow Django to start
    cat > /app/.env << EOF
SECRET_KEY=temporary-key-for-setup
DEBUG=False
ALLOWED_HOSTS=localhost
POSTGRES_DB=${POSTGRES_DB:-iss_portal_db}
POSTGRES_USER=${POSTGRES_USER:-iss_user}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-change-this-password}
DATABASE_URL=postgresql://${POSTGRES_USER:-iss_user}:${POSTGRES_PASSWORD:-change-this-password}@db:5432/${POSTGRES_DB:-iss_portal_db}
FIELD_ENCRYPTION_KEY=$TEMP_FERNET_KEY
TIME_ZONE=America/Toronto
EOF
    
    # Run interactive setup to get real values
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
