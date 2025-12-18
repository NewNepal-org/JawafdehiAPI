# Testing Instructions

## Framework
- pytest with pytest-django
- hypothesis for property-based testing
- Fixtures in conftest.py

## Test Structure
```
tests/
├── api/           # API endpoint tests
├── cases/         # Cases app tests
├── e2e/           # End-to-end tests
├── conftest.py    # Shared fixtures
└── strategies.py  # Hypothesis strategies
```

## Patterns
- Use authentic Nepali names in test data
- Test permission boundaries thoroughly
- Property-based testing for data validation
- Mock external services (NES API)

## Commands
```bash
poetry run pytest
poetry run pytest --cov=.
poetry run pytest -k "test_name"
```