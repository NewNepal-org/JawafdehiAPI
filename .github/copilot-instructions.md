# GitHub Copilot Instructions - JawafdehiAPI

## Primary Reference
Read `AGENTS.md` in this directory for complete context and workflow.

## Critical Rules
- Use `poetry run` for all Python commands
- Follow Django 5.2+ conventions
- Maintain case revision audit trails
- Use authentic Nepali names in examples
- Never commit secrets or sensitive data

## Code Patterns
- Models in `cases/models.py` with proper relationships
- DRF serializers with validation
- Permission-based views using `rules` library
- Comprehensive test coverage with pytest + hypothesis

## Quick Commands
```bash
poetry run python manage.py runserver
poetry run pytest
poetry run black . && poetry run isort .
```