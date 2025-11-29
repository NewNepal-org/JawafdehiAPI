# Test Refactoring Summary

## Completed Refactoring

### 1. Created Shared Modules

#### `tests/strategies.py` (NEW)
Consolidated all Hypothesis strategies from multiple test files:
- **Entity ID strategies**: `valid_entity_id()`, `entity_id_list()`, `invalid_entity_id()`, `simple_entity_id()`, `simple_entity_id_list()`
- **Text strategies**: `text_list()`, `tag_list()`, `simple_text_list()`
- **Timeline strategies**: `timeline_entry()`, `timeline_list()`
- **Evidence strategies**: `evidence_entry()`, `evidence_list()`
- **Case data strategies**: `minimal_case_data()`, `complete_case_data()`, `complete_case_data_with_timeline()`, `simple_complete_case_data()`
- **Source data strategies**: `valid_source_data()`, `source_data_missing_title()`, `source_data_missing_description()`, `source_data_with_empty_title()`, `source_data_with_empty_description()`
- **User data strategies**: `user_with_role()`

**Lines saved**: ~250 lines of duplicate strategy code

#### `tests/conftest.py` (UPDATED)
Added shared helper functions:
- `create_user_with_role()` - Creates users with proper roles and permissions
- `create_mock_request()` - Creates mock Django requests with user attached
- `request_factory` fixture - Provides RequestFactory for tests

**Lines saved**: ~100 lines of duplicate user creation code

### 2. Updated Test Files

#### `tests/test_admin_case_management.py`
- ✅ Removed duplicate Hypothesis strategies
- ✅ Removed duplicate `create_user_with_role()` function
- ✅ Removed duplicate `can_transition_to_state()` helper
- ✅ Now uses `can_transition_case_state()` from `cases.rules.predicates`
- ✅ Imports strategies from `tests/strategies.py`
- ✅ Imports `create_user_with_role` from `tests/conftest.py`

**Lines removed**: ~135 lines

#### `tests/test_case_model.py`
- ✅ Removed duplicate Hypothesis strategies
- ✅ Imports `minimal_case_data` and `complete_case_data` from `tests/strategies.py`

**Lines removed**: ~70 lines

#### `tests/test_custom_fields.py`
- ✅ Removed duplicate Hypothesis strategies
- ✅ Imports `text_list`, `timeline_list`, `evidence_list` from `tests/strategies.py`

**Lines removed**: ~90 lines

#### `tests/test_document_source.py`
- ✅ Removed duplicate Hypothesis strategies
- ✅ Imports all source data strategies from `tests/strategies.py`

**Lines removed**: ~75 lines

#### `tests/test_public_api.py`
- ✅ Removed duplicate Hypothesis strategies
- ✅ Imports `complete_case_data_with_timeline`, `valid_source_data`, `tag_list` from `tests/strategies.py`

**Lines removed**: ~110 lines

#### `tests/test_role_based_permissions.py`
- ✅ Removed duplicate Hypothesis strategies
- ✅ Removed duplicate `create_user_with_role()` function
- ✅ Removed duplicate `create_mock_request()` function
- ✅ Imports `simple_complete_case_data`, `user_with_role` from `tests/strategies.py`
- ✅ Imports `create_user_with_role`, `create_mock_request` from `tests/conftest.py`

**Lines removed**: ~160 lines

#### `tests/test_case_creator_access.py`
- ✅ Simplified fixtures to use `create_user_with_role()`
- ✅ Updated all test functions to use `create_mock_request()`
- ✅ Removed duplicate permission setup code

**Lines removed**: ~70 lines

#### `tests/test_document_source_admin.py`
- ✅ Simplified fixtures to use `create_user_with_role()`
- ✅ Updated test functions to use `create_mock_request()`
- ✅ Removed duplicate user creation code

**Lines removed**: ~50 lines

#### `tests/e2e/test_admin_e2e.py`
- ✅ Removed duplicate `create_user_with_role()` function
- ✅ Updated imports to use shared functions
- ⚠️ **PARTIAL**: Still has ~10 instances of inline `RequestFactory()` usage that should be replaced with `create_mock_request()`

**Lines removed**: ~95 lines

### 3. Key Improvements

#### Permission Checking
- **Before**: Test helper function `can_transition_to_state()` duplicated business logic
- **After**: Tests now use actual predicate `can_transition_case_state()` from `cases.rules.predicates`
- **Benefit**: Tests validate actual production code, not a test-only reimplementation

#### User Creation
- **Before**: 3 different implementations of `create_user_with_role()` across test files
- **After**: Single implementation in `conftest.py` used by all tests
- **Benefit**: Consistent user setup, easier to maintain permissions

#### Hypothesis Strategies
- **Before**: Same strategies duplicated in 6+ test files
- **After**: All strategies in `tests/strategies.py`
- **Benefit**: Single source of truth, easier to update entity ID formats

## Total Impact

### Lines of Code Reduced
- **Duplicate strategies removed**: ~250 lines
- **Duplicate helper functions removed**: ~200 lines
- **Simplified test setup**: ~100 lines
- **Total**: ~550 lines of duplicate code eliminated

### Maintainability Improvements
1. **Single source of truth** for test data generation
2. **Consistent user creation** across all tests
3. **Tests validate actual business logic** (predicates) instead of test-only helpers
4. **Easier to update** - changes to entity ID format only need to be made in one place

## Remaining Work

### `tests/e2e/test_admin_e2e.py`
The file still has ~10 instances of inline RequestFactory usage that should be replaced:

```python
# Current pattern (repeated ~10 times):
from django.test import RequestFactory
factory = RequestFactory()
request = factory.get('/')
request.user = some_user

# Should be:
request = create_mock_request(some_user)
```

**Estimated additional savings**: ~30 lines

### `tests/e2e/test_public_api_e2e.py`
This file doesn't have duplicate code issues - it's already clean.

## Testing Recommendations

After this refactoring, run the full test suite to ensure:
1. All imports resolve correctly
2. Hypothesis strategies generate valid data
3. Permission checks work with the actual predicates
4. User creation sets up permissions correctly

```bash
pytest tests/ -v
```

## Future Improvements

1. **Consider parameterized fixtures** for common user role combinations
2. **Add type hints** to strategy functions for better IDE support
3. **Document strategy usage** in tests/strategies.py docstrings
4. **Create fixture for CaseAdmin** instance to reduce repetition in e2e tests
