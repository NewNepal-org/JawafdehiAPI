#!/bin/bash
set -e

# Test script for Jawafdehi API
# Uses SQLite for local testing to avoid PostgreSQL setup requirements

echo "Running tests with SQLite database..."
DATABASE_URL=sqlite:///test_db.sqlite3 poetry run pytest "$@"
