#!/bin/bash
set -e

# Test script for Jawafdehi API
# Uses SQLite for local testing to avoid PostgreSQL setup requirements

echo "Running tests with SQLite database..."

# Create a temporary SQLite database file
TEMP_DB=$(mktemp -t test_db_XXXXXX.sqlite3)

# Ensure cleanup on exit
trap 'rm -f "$TEMP_DB"' EXIT

# Run tests with temporary database
DATABASE_URL="sqlite:///$TEMP_DB" poetry run pytest "$@"