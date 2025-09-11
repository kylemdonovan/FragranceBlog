#!/bin/bash

# This script is run by whatever silly goose program you use on every deploy.
# The 'set -e' command ensures that if any command fails, the script will exit immediately.
#!/bin/bash

set -e

echo "--- Running One-Time Database Table Creation ---"
psql $DATABASE_URL <<EOF
-- Create the Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash TEXT,
    is_admin BOOLEAN,
    confirmed BOOLEAN,
    confirmed_on TIMESTAMP
);

-- Create the Posts table
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(140) NOT NULL,
    slug VARCHAR(150) NOT NULL UNIQUE,
    body TEXT NOT NULL,
    image_url VARCHAR(255),
    image_public_id VARCHAR(255),
    timestamp TIMESTAMP,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status BOOLEAN,
    published_at TIMESTAMP
);

-- Create the Tags table
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- Create the Comments table
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    body TEXT NOT NULL,
    timestamp TIMESTAMP,
    user_id INTEGER NOT NULL REFERENCES users(id),
    post_id INTEGER NOT NULL REFERENCES posts(id)
);

-- Create the Subscribers table
CREATE TABLE subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE,
    subscribed_at TIMESTAMP
);

-- Create the Post-Tags association table
CREATE TABLE post_tags (
    post_id INTEGER NOT NULL REFERENCES posts(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    PRIMARY KEY (post_id, tag_id)
);
EOF
echo "--- Database Tables Created Successfully ---"

echo "--- Running Database Migrations (will do nothing, which is OK) ---"
flask db upgrade

echo "--- Starting Gunicorn Server ---"
gunicorn wsgi:app
