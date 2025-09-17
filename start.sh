#!/bin/bash
set -e

echo "--- Wiping and rebuilding database schema from scratch ---"
psql $DATABASE_URL <<EOF

-- Drop all tables to ensure a clean state
DROP TABLE IF EXISTS alembic_version, comment_likes, post_tags, comments, subscribers, posts, users CASCADE;

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
    post_id INTEGER NOT NULL REFERENCES posts(id),
    parent_id INTEGER REFERENCES comments(id)
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

-- Create the CommentLikes table
CREATE TABLE comment_likes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    comment_id INTEGER NOT NULL REFERENCES comments(id),
    timestamp TIMESTAMP
);

EOF
echo "--- Database is clean and ready ---"

echo "--- Starting Gunicorn Server ---"
gunicorn wsgi:app
