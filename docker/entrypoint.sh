#!/bin/sh
set -e

echo "Waiting for PostgreSQL database..."
while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
  sleep 0.5
done
echo "PostgreSQL is ready!"

python manage.py migrate --noinput

exec "$@"
