# JawafdehiAPI - Repository Structure Guide

## Service Overview
Django accountability platform backend for Jawafdehi civic tech project.

## Directory Structure

```
services/JawafdehiAPI/
├── AGENTS.md              # Cross-tool entry point
├── manage.py              # Django management
├── pyproject.toml         # Poetry dependencies
├── .env.example           # Environment template
│
├── config/                # Django project settings
│   ├── settings.py        # Main configuration
│   ├── urls.py            # Root URL routing
│   └── wsgi.py            # WSGI application
│
├── cases/                 # Core allegation management
│   ├── models.py          # Data models
│   ├── serializers.py     # DRF serializers
│   ├── api_views.py       # API endpoints
│   ├── admin.py           # Admin interface
│   ├── rules/             # Permission rules
│   └── migrations/        # Database migrations
│
├── agni/                  # AI assistant integration
├── tests/                 # Test suite
│   ├── api/               # API tests
│   ├── e2e/               # End-to-end tests
│   ├── conftest.py        # Pytest fixtures
│   └── strategies.py      # Hypothesis strategies
│
├── docs/                  # Service documentation
├── static/                # Static assets
├── templates/             # Django templates
└── scripts/               # Utility scripts
```

## Key Files

- **AGENTS.md** - Primary agent entry point
- **pyproject.toml** - Poetry configuration and dependencies
- **config/settings.py** - Django settings with environment variables
- **cases/models.py** - Core data models for allegations
- **tests/conftest.py** - Shared test fixtures

## Integration Points

- **Nepal Entity Service** - Entity data via git repo or local package
- **Frontend (Jawafdehi)** - React app consuming this API
- **PostgreSQL** - Primary database
- **Agni AI** - AI assistant for case analysis

## Development Workflow

1. **Check specs** - Look in `.kiro/specs/` at meta-repo root
2. **Follow Django patterns** - Models → Serializers → Views → URLs
3. **Test thoroughly** - Unit, integration, API tests
4. **Use Poetry** - All Python commands via `poetry run`