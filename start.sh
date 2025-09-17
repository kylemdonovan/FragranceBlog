#!/bin/bash
set -e

echo "--- Manually updating database schema for replies and likes ---"
psql $DATABASE_URL <<EOF

-- Add the parent_id column to the comments table for replies
ALTER TABLE comments ADD COLUMN parent_id INTEGER REFERENCES comments(id);

-- Create the new table for comment likes
CREATE TABLE comment_likes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    comment_id INTEGER NOT NULL REFERENCES comments(id),
    timestamp TIMESTAMP
);

EOF
echo "--- Database schema updated successfully ---"

echo "--- Running database migrations (will do nothing, which is OK) ---"
flask db upgrade

echo "--- Starting Gunicorn Server ---"
gunicorn wsgi:app
