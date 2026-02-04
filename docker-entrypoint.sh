#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U iss_user > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready!"

echo "Fixing permissions for mounted volumes..."
mkdir -p /app/staticfiles /app/media
chown -R appuser:appuser /app/staticfiles /app/media

echo "Running database migrations..."
su appuser -c "python manage.py migrate --noinput"

echo "Collecting static files..."
su appuser -c "python manage.py collectstatic --noinput --clear"

echo "Creating initial data..."
su appuser -c "python manage.py create_initial_data" || true

echo "Starting application..."
exec su appuser -c "$*"
