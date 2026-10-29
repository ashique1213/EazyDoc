#!/bin/sh
set -e

# Wait for PostgreSQL database using Python socket check
echo "Waiting for PostgreSQL database at ${DATABASE_HOST:-localhost}:${DATABASE_PORT:-5432}..."
python -c "
import socket, sys, time, os
host = os.environ.get('DATABASE_HOST', 'localhost')
port = int(os.environ.get('DATABASE_PORT', 5432))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
start = time.time()
while True:
    try:
        s.connect((host, port))
        s.close()
        break
    except socket.error:
        if time.time() - start > 60:
            sys.stderr.write('Timeout waiting for PostgreSQL database\n')
            sys.exit(1)
        time.sleep(0.5)
"
echo "PostgreSQL is ready!"

# Only run migrations when explicitly requested or starting the primary web backend
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  python manage.py migrate --noinput
fi

exec "$@"
