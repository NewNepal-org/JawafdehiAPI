# Feature Flag: EXPOSE_CASES_IN_REVIEW

## Overview

This feature flag controls whether cases in `IN_REVIEW` state are exposed via the public API endpoints.

**Default Value:** `True` (IN_REVIEW cases are exposed by default)

## Configuration

Set the environment variable in your `.env` file:

```bash
# Disable the feature (hide IN_REVIEW cases)
EXPOSE_CASES_IN_REVIEW=False

# Enable the feature (default - expose IN_REVIEW cases)
EXPOSE_CASES_IN_REVIEW=True
```

## Behavior

### When Enabled (Default: `EXPOSE_CASES_IN_REVIEW=True`)

- **GET /api/cases/**: Returns both `PUBLISHED` and `IN_REVIEW` cases
- **GET /api/cases/{id}/**: Returns both `PUBLISHED` and `IN_REVIEW` cases
- **GET /api/sources/**: Returns sources referenced in both `PUBLISHED` and `IN_REVIEW` cases
- **Response**: Includes `state` field showing "PUBLISHED" or "IN_REVIEW"
- **Audit History**: Includes both `PUBLISHED` and `IN_REVIEW` versions

### When Disabled (`EXPOSE_CASES_IN_REVIEW=False`)

- **GET /api/cases/**: Returns only `PUBLISHED` cases
- **GET /api/cases/{id}/**: Returns only `PUBLISHED` cases
- **GET /api/sources/**: Returns sources referenced in `PUBLISHED` cases only
- **Response**: Includes `state` field showing only "PUBLISHED"
- **Audit History**: Includes only `PUBLISHED` versions

## Implementation Details

### Modified Files

1. **config/settings.py**: Feature flag configuration (default: True)
2. **cases/api_views.py**: `CaseViewSet.get_queryset()` and `DocumentSourceViewSet.get_queryset()` check the flag
3. **cases/serializers.py**: `CaseSerializer` always includes `state` field, `CaseDetailSerializer.get_audit_history()` respects the flag
4. **.env.example**: Feature flag documentation updated to reflect new default

### Logic Changes

- **CaseViewSet**: Filters by `state__in=[PUBLISHED, IN_REVIEW]` when flag is enabled (default)
- **DocumentSourceViewSet**: Includes sources from IN_REVIEW cases when flag is enabled (default)
- **CaseSerializer**: Always includes `state` field in response
- **Audit History**: Includes IN_REVIEW versions in audit trail when flag is enabled (default)

## Deployment

**Default Behavior (No Configuration Required):**
- IN_REVIEW cases are now publicly accessible by default
- No environment variable needs to be set

**To Hide IN_REVIEW Cases:**

1. Set environment variable: `EXPOSE_CASES_IN_REVIEW=False`
2. Restart the application
3. No database migrations required
4. No code deployment required

**To Re-enable IN_REVIEW Cases:**

1. Remove or set environment variable: `EXPOSE_CASES_IN_REVIEW=True`
2. Restart the application

## Testing

Test the feature flag behavior:

```bash
# Test default behavior (IN_REVIEW cases included)
curl http://localhost:8000/api/cases/
# Should include both PUBLISHED and IN_REVIEW cases with state field

# Disable flag in .env to hide IN_REVIEW cases
echo "EXPOSE_CASES_IN_REVIEW=False" >> .env

# Restart server and test again
curl http://localhost:8000/api/cases/
# Should now only include PUBLISHED cases
```
