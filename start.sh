#!/bin/bash

# This script is run by whatever silly goose program you use on every deploy.
# The 'set -e' command ensures that if any command fails, the script will exit immediately.
set -e

echo "--- Running Database Migrations ---"
flask db upgrade

echo "--- Starting Gunicorn Server ---"
gunicorn wsgi:app