# Cursor Rules - JawafdehiAPI

## Context
Django accountability platform for Nepal's transparency initiative. See `AGENTS.md` for complete context.

## Core Rules

### Django Development
- Use Poetry: `poetry run python manage.py <command>`
- Follow Django 5.2+ patterns and conventions
- Maintain case revision system integrity
- Use DRF for all API endpoints

### Code Quality
- Format: `poetry run black . && poetry run isort .`
- Test: `poetry run pytest` before commits
- Use authentic Nepali names in examples
- Follow established permission hierarchy

### Security
- Never commit `.env` files
- Use Django migrations for schema changes
- Validate user permissions on all operations
- Maintain audit trails for case revisions

### Architecture
- Models → Serializers → Views → URLs pattern
- Use `rules` library for permissions
- Integrate with Nepal Entity Service
- Follow RESTful API design

Refer to project handbook at meta-repo root (if it exists) for detailed architecture.