# JawafdehiAPI - Django Accountability Platform

## What This Repo Is

JawafdehiAPI is the core Django backend service for Jawafdehi, Nepal's civic tech platform for transparency and accountability. It provides a RESTful API for managing corruption allegations, evidence, and entity responses with a comprehensive permissions system.

**Key Responsibilities:**
- Corruption case management with revision system
- Evidence and source documentation
- Entity response handling
- User role management (Admin/Moderator/Contributor)
- Integration with Nepal Entity Service (NES)
- Public API for transparency data

## Non-Negotiable Rules

### Security & Data Integrity
- **NEVER commit secrets** - Use `.env` files (gitignored) with `.env.example` templates
- **All database changes** must go through Django migrations
- **User permissions** must follow the established role hierarchy (Admin > Moderator > Contributor)
- **Case revisions** maintain complete audit trails - never delete revision history
- **API endpoints** require proper authentication and authorization

### Code Quality
- **Poetry only** - Use `poetry run` for all Python commands, never pip
- **Django 5.2+** - Follow Django best practices and conventions
- **Testing required** - pytest with hypothesis for property-based testing
- **Format with black** (line length: 88) and isort (black profile)
- **Type hints encouraged** but not enforced

### Nepali Context
- **Use authentic Nepali names** in examples, fixtures, and documentation
- **Bilingual support** - Equal treatment for English and Nepali content
- **WCAG 2.1 AA compliance** for all user-facing features

## Key Paths

```
services/JawafdehiAPI/
├── manage.py              # Django management
├── pyproject.toml         # Poetry dependencies
├── config/                # Django settings
├── cases/                 # Core allegation models & API
├── agni/                  # AI assistant integration
├── tests/                 # Test suite
├── docs/                  # Service documentation
├── static/                # Static assets
├── templates/             # Django templates
└── scripts/               # Utility scripts
```

## Expected Workflow

### For Non-Trivial Features
1. **Check specs first** - Look in `.kiro/specs/` at meta-repo root
2. **Create spec if missing** - Use requirements.md, design.md, tasks.md structure
3. **Follow Django patterns** - Models → Serializers → Views → URLs
4. **Test thoroughly** - Unit tests, integration tests, API tests

### For Bug Fixes
1. **Write failing test** that reproduces the issue
2. **Fix the code** to make the test pass
3. **Verify no regressions** with full test suite

## Essential Commands

### Setup & Development
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run migrations
poetry run python manage.py migrate

# Create superuser
poetry run python manage.py createsuperuser

# Start development server
poetry run python manage.py runserver

# Create user groups
poetry run python manage.py create_groups
```

### Testing & Quality
```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=.

# Format code
poetry run black .
poetry run isort .

# Lint code
poetry run flake8
```

### Database Operations
```bash
# Make migrations
poetry run python manage.py makemigrations

# Apply migrations
poetry run python manage.py migrate

# Seed test data
poetry run python manage.py seed_allegations
```

## Architecture Notes

### Core Models
- **Case** - Corruption allegations with revision system
- **Evidence** - Supporting documentation and proof
- **Source** - Reference materials and citations
- **Response** - Entity responses to allegations

### Permission System
- **Admin** - Full system access, manages moderators
- **Moderator** - Manages contributors, reviews cases
- **Contributor** - Creates cases, limited to assigned cases

### API Design
- **RESTful endpoints** with DRF
- **OpenAPI documentation** via drf-spectacular
- **Filtering and search** with django-filter
- **CORS enabled** for frontend integration

## Integration Points

- **Nepal Entity Service** - Entity data and validation
- **Frontend (Jawafdehi)** - React public interface
- **Agni AI** - AI assistant for case analysis
- **PostgreSQL** - Primary database (SQLite for dev)

## Quick Reference

- **Admin Panel**: `http://localhost:8000/admin`
- **API Root**: `http://localhost:8000/api/`
- **API Docs**: `http://localhost:8000/api/schema/swagger-ui/`
- **Health Check**: `http://localhost:8000/health/`

---

*For detailed documentation, see `docs/` directory. For project-wide context, refer to the agent-kit handbook at the meta-repo root (if it exists).*