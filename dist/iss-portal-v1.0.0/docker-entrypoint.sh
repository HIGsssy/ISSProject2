#!/bin/bash
set -e

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
