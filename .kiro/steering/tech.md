# JawafdehiAPI - Technical Standards

## Django Development Rules

### Package Management
- **Poetry only** - Use `poetry run` for all Python commands
- **Virtual environments** - Poetry manages automatically
- **Dependencies** - Add via `poetry add <package>`

### Django Conventions
- **Django 5.2+** - Follow latest Django patterns
- **DRF** - Use Django REST Framework for all APIs
- **Migrations** - All schema changes via Django migrations
- **Settings** - Environment-based configuration

### Code Quality
- **Formatter**: black (line length: 88)
- **Import Sorter**: isort (black profile)
- **Linter**: flake8
- **Type Hints**: Encouraged but not enforced

### Testing
- **Framework**: pytest with pytest-django
- **Property Testing**: hypothesis for robust test data
- **Structure**: Mirror source in `tests/` directory
- **Coverage**: Unit, integration, and E2E tests

### Security
- **Environment Variables** - Never commit `.env` files
- **Permissions** - Use `rules` library for authorization
- **Audit Trails** - Maintain complete revision history
- **Django Security** - Follow Django security best practices

### Architecture Patterns
- **Models** → **Serializers** → **Views** → **URLs**
- **Permission-based views** using django-rules
- **RESTful API design** with proper HTTP methods
- **Integration patterns** with Nepal Entity Service

## Essential Commands

```bash
# Development
poetry run python manage.py runserver
poetry run python manage.py migrate
poetry run python manage.py createsuperuser

# Testing & Quality
poetry run pytest
poetry run black .
poetry run isort .
poetry run flake8

# Database
poetry run python manage.py makemigrations
poetry run python manage.py migrate
```