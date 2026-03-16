# Jawafdehi API (JDS) - Product Guide

## Overview

Django-based public accountability platform for tracking allegations of corruption and misconduct by public entities in Nepal. This API serves as the backend for the Jawafdehi project (https://jawafdehi.org, beta at https://beta.jawafdehi.org), a civic tech platform promoting transparency and accountability in Nepali governance.

## Core Features

- **Case Management**: Track allegations with complete revision history
- **Entity Management**: Manage profiles of public officials and organizations
- **Role-Based Permissions**: Admin/Moderator/Contributor roles with django-rules
- **Audit Trails**: Complete version history for transparency
- **OpenAPI Documentation**: Auto-generated API docs via drf-spectacular
- **Admin Interface**: Jazzmin-powered Bootstrap 4 admin panel

## Technology Stack

- **Language**: Python 3.12+
- **Package Manager**: Poetry
- **Framework**: Django 5.2+, Django REST Framework
- **Database**: PostgreSQL (via psycopg2-binary)
- **Admin**: Jazzmin (Bootstrap 4)
- **API Docs**: drf-spectacular (OpenAPI)
- **Permissions**: django-rules
- **Testing**: pytest, pytest-django, hypothesis
- **Server**: Gunicorn

## Project Structure

```
services/jawafdehi-api/
├── config/                # Django project settings
│   ├── settings.py       # Main settings
│   ├── urls.py           # URL routing
│   └── wsgi.py           # WSGI application
├── cases/                 # Main Django app
│   ├── models.py         # Data models
│   ├── serializers.py    # DRF serializers
│   ├── api_views.py      # API views
│   ├── admin.py          # Admin interface
│   ├── rules/            # Permission rules
│   ├── migrations/       # Database migrations
│   ├── static/           # Static files
│   └── templates/        # HTML templates
├── tests/                 # Test suite
│   ├── api/              # API tests
│   ├── e2e/              # End-to-end tests
│   ├── conftest.py       # Pytest configuration
│   └── strategies.py     # Hypothesis strategies
├── docs/                  # Documentation
├── static/                # Project-wide static files
├── staticfiles/           # Collected static files
├── tmp/                   # Temporary scripts
└── pyproject.toml        # Poetry configuration
```

## Common Commands

```bash
# Install dependencies
poetry install

# Run development server
poetry run python manage.py runserver

# Run migrations
poetry run python manage.py migrate

# Create superuser
poetry run python manage.py createsuperuser

# Collect static files
poetry run python manage.py collectstatic

# Run tests
poetry run pytest
```

## Environment Configuration

Required environment variables:

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated hostnames
- `CSRF_TRUSTED_ORIGINS`: Comma-separated origins
- `DATABASE_URL`: PostgreSQL connection string
- `EXPOSE_CASES_IN_REVIEW`: Feature flag (True/False)

## Code Quality Standards

- **Formatter**: black (line length: 88)
- **Import Sorter**: isort (black profile)
- **Linter**: flake8
- **Type Hints**: Encouraged but not enforced
- **Testing**: pytest with hypothesis for property-based testing

## Testing Conventions

- **Framework**: pytest with fixtures in `conftest.py`
- **Property Testing**: hypothesis for generating test data
- **Test Data**: Use authentic Nepali names and entities in fixtures
- **Coverage**: Unit, integration, and E2E tests
- **Structure**: Mirror source structure in `tests/` directory

## Deployment

- **Platform**: Google Cloud Platform
- **Compute**: Cloud Run
- **Database**: Cloud SQL PostgreSQL 18
- **CI/CD**: Cloud Build
- **Container**: Docker with python:3.12-slim base image
- **Port**: 8080
- **Static Files**: Collected to `staticfiles/`

## Key Principles

- **Open Data**: All case data is open and accessible
- **Transparency**: Complete audit trails and version history
- **Nepali Context**: Use authentic Nepali names, organizations, and locations in examples and documentation
- **Package Structure**: Flat module structure under main package name
- **Config**: Environment-based configuration with `.env` files
- **Migrations**: Django migration system for database changes
