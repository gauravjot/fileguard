#!/bin/sh

# Wait for the database to be ready
# Use the environment variables directly
echo "Waiting for database on $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
  echo "Connecting to database at $DB_HOST:$DB_PORT..."
done
echo "Database ready!"

# Apply database migrations
echo "Applying database migrations..."
cd /opt/fileguard
python manage.py makemigrations
python manage.py migrate

# Start the application (supervisord)
echo "Starting supervisord..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisor.conf