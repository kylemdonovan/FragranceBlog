#!/bin/bash
set -e
flask db upgrade
gunicorn wsgi:app
