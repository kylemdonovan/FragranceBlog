#!/bin/bash
set -e

echo "--- Generating new database migration script on the server ---"
flask db migrate -m "Add comment replies and likes functionality"

echo "--- Applying all database migrations ---"
flask db upgrade

echo "--- Starting Gunicorn Server ---"
gunicorn wsgi:app
