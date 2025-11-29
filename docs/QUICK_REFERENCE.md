# Test Suite Quick Reference

## Project Structure

```
jawafdehi/
├── docs/                                    # All documentation
│   ├── API_DOCUMENTATION.md
│   ├── COMPLETE_REFACTORING_SUMMARY.md
│   ├── ENTITY_MIGRATION_SUMMARY.md
│   ├── FEATURE_FLAG_EXPOSE_CASES_IN_REVIEW.md
│   ├── IMPORT_REFACTORING.md
│   ├── Nepal Public Accountability Portal.md
│   └── REFACTORING_SUMMARY.md
│
├── tests/
│   ├── api/                                 # API tests
│   │   ├── test_public_api.py
│   │   ├── test_entity_api.py
│   │   ├── test_api_documentation_integration.py
│   │   └── test_openapi_documentation.py
│   │
│   ├── e2e/                                 # End-to-end tests
│   │   ├── test_admin_e2e.py
│   │   └── test_public_api_e2e.py
│   │
│   ├── conftest.py                          # Shared fixtures and helpers
│   ├── strategies.py                        # Hypothesis strategies
│   │
│   ├── test_admin_case_management.py        # Admin tests
│   ├── test_case_creator_access.py
│   ├── test_case_model.py                   # Model tests
│   ├── test_custom_fields.py
│   ├── test_document_source.py
│   ├── test_document_source_admin.py
│   ├── test_feature_flag_expose_cases_in_review.py
│   ├── test_nes_import.py
│   └── test_role_based_permissions.py       # Permission tests
│
└── cases/                                   # Application code
    ├── models.py
    ├── admin.py
    ├── rules/
    │   └── predicates.py                    # Permission predicates
    └── ...
```

## Shared Test Utilities

### `tests/conftest.py`

**Fixtures:**
```python
@pytest.fixture
def request_factory():
    """Provides Django RequestFactory"""
```

**Helper Functions:**
```python
create_entities_from_ids(entity_ids)
    # Creates JawafEntity objects from ID strings

create_case_with_entities(**kwargs)
    # Creates Case with entity relationships

create_document_source_with_entities(**kwargs)
    # Creates DocumentSource with entity relationships

create_user_with_role(username, email, role, password="testpass123")
    # Creates user with proper role and permissions
    # Roles: 'Admin', 'Moderator', 'Contributor'

create_mock_request(user, method='get', path='/')
    # Creates mock Django request with user attached
```

### `tests/strategies.py`

**Entity Strategies:**
```python
valid_entity_id()              # Generates valid NES entity IDs
entity_id_list()               # List of entity IDs
invalid_entity_id()            # Invalid entity IDs for negative tests
simple_entity_id()             # Simpler/faster entity IDs
simple_entity_id_list()        # List of simple entity IDs
```

**Text Strategies:**
```python
text_list()                    # List of text strings
tag_list()                     # List of tags
simple_text_list()             # Simpler text lists
```

**Timeline Strategies:**
```python
timeline_entry()               # Single timeline entry
timeline_list()                # List of timeline entries
```

**Evidence Strategies:**
```python
evidence_entry()               # Single evidence entry
evidence_list()                # List of evidence entries
```

**Case Data Strategies:**
```python
minimal_case_data()            # Minimal data for DRAFT state
complete_case_data()           # Complete data for IN_REVIEW/PUBLISHED
complete_case_data_with_timeline()  # Complete with timeline/tags
simple_complete_case_data()    # Simpler/faster complete data
```

**Source Data Strategies:**
```python
valid_source_data()            # Valid DocumentSource data
source_data_missing_title()    # Missing title (for negative tests)
source_data_missing_description()
source_data_with_empty_title()
source_data_with_empty_description()
```

**User Strategies:**
```python
user_with_role(role)           # User data with specified role
```

## Common Test Patterns

### Property-Based Test with Hypothesis

```python
from hypothesis import given, settings
from tests.strategies import complete_case_data
from tests.conftest import create_case_with_entities

@pytest.mark.django_db
@settings(max_examples=20)
@given(case_data=complete_case_data())
def test_something(case_data):
    case = create_case_with_entities(**case_data)
    # assertions...
```

### Testing Permissions

```python
from cases.rules.predicates import can_transition_case_state
from tests.conftest import create_user_with_role

@pytest.mark.django_db
def test_permission():
    user = create_user_with_role('testuser', 'test@example.com', 'Contributor')
    # Use actual predicate, not test helper
    can_transition = can_transition_case_state(user, case, CaseState.PUBLISHED)
    assert not can_transition
```

### Testing Admin Views

```python
from tests.conftest import create_mock_request, create_user_with_role
from cases.admin import CaseAdmin

@pytest.mark.django_db
def test_admin_view():
    admin_user = create_user_with_role('admin', 'admin@test.com', 'Admin')
    request = create_mock_request(admin_user)
    
    admin_instance = CaseAdmin(Case, None)
    has_permission = admin_instance.has_change_permission(request, case)
    assert has_permission
```

### API Tests

```python
from rest_framework.test import APIClient
from tests.conftest import create_case_with_entities

@pytest.mark.django_db
def test_api_endpoint():
    case = create_case_with_entities(
        title="Test Case",
        alleged_entities=["entity:person/test"],
        case_type=CaseType.CORRUPTION,
        state=CaseState.PUBLISHED
    )
    
    client = APIClient()
    response = client.get('/api/cases/')
    assert response.status_code == 200
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test groups
pytest tests/api/ -v                    # API tests only
pytest tests/e2e/ -v                    # E2E tests only
pytest tests/test_case_model.py -v     # Single file

# With coverage
pytest tests/ --cov=cases --cov-report=html

# Specific test function
pytest tests/test_case_model.py::test_new_cases_start_in_draft_state -v

# Run fast (skip slow hypothesis tests)
pytest tests/ -v -m "not slow"
```

## Import Guidelines

### Standard Import Order

```python
# 1. Standard library
import pytest
from datetime import datetime

# 2. Third party (Django, hypothesis, etc.)
from django.core.exceptions import ValidationError
from hypothesis import given, settings

# 3. Local application
from cases.models import Case, CaseState, CaseType
from cases.rules.predicates import can_transition_case_state
from tests.conftest import create_case_with_entities
from tests.strategies import complete_case_data
```

### What NOT to Do

❌ **Don't use try/except for imports:**
```python
# Bad - models are implemented
try:
    from cases.models import Case
except ImportError:
    pytest.skip("...")
```

❌ **Don't import inline:**
```python
# Bad
def test_something():
    from cases.admin import SomeAdmin
    ...
```

❌ **Don't duplicate strategies:**
```python
# Bad - use tests/strategies.py instead
@st.composite
def valid_entity_id(draw):
    # duplicate implementation
```

### What TO Do

✅ **Import at top of file:**
```python
from cases.models import Case
```

✅ **Use shared strategies:**
```python
from tests.strategies import valid_entity_id
```

✅ **Use shared helpers:**
```python
from tests.conftest import create_user_with_role
```

✅ **Use production code in tests:**
```python
from cases.rules.predicates import can_transition_case_state
```

## Key Files to Know

- **`tests/conftest.py`** - Shared fixtures and helper functions
- **`tests/strategies.py`** - All Hypothesis strategies for test data generation
- **`cases/rules/predicates.py`** - Permission predicates (use in tests, don't reimplement)
- **`cases/models.py`** - Model definitions
- **`cases/admin.py`** - Admin configuration

## Getting Help

- **Refactoring details**: See `docs/COMPLETE_REFACTORING_SUMMARY.md`
- **Import changes**: See `docs/IMPORT_REFACTORING.md`
- **Project standards**: See `.kiro/steering/project-standards.md`
