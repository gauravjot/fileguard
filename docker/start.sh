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

# Check if config folder exists
if [ ! -d /opt/fileguard/config ]; then
  echo "\nConfig folder not found, creating..."
  mkdir -p /opt/fileguard/config
else
  echo "\nConfig folder exists, checking for encryption key..."
fi
# Check if encryption key exists in config folder
if [ ! -f /opt/fileguard/config/encryption_key.txt ]; then
  echo "-- Encryption key not found, generating a new one..."
  python manage.py generate_encryption_key
else
  echo "-- Encryption key found, using existing key."
fi

# Start the application (supervisord)
echo "\nStarting supervisord..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisor.conf