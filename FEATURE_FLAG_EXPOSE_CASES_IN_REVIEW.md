# Feature Flag: EXPOSE_CASES_IN_REVIEW

## Overview

This feature flag controls whether cases in `IN_REVIEW` state are exposed via the public API endpoints.

## Configuration

Set the environment variable in your `.env` file:

```bash
# Enable the feature
EXPOSE_CASES_IN_REVIEW=True

# Disable the feature (default)
EXPOSE_CASES_IN_REVIEW=False
```

## Behavior

### When Disabled (Default: `EXPOSE_CASES_IN_REVIEW=False`)

- **GET /api/cases/**: Returns only `PUBLISHED` cases
- **GET /api/cases/{id}/**: Returns only `PUBLISHED` cases
- **GET /api/sources/**: Returns sources referenced in `PUBLISHED` cases only
- **Response**: Does NOT include `state` field in case serialization
- **Audit History**: Includes only `PUBLISHED` versions

### When Enabled (`EXPOSE_CASES_IN_REVIEW=True`)

- **GET /api/cases/**: Returns both `PUBLISHED` and `IN_REVIEW` cases
- **GET /api/cases/{id}/**: Returns both `PUBLISHED` and `IN_REVIEW` cases
- **GET /api/sources/**: Returns sources referenced in both `PUBLISHED` and `IN_REVIEW` cases
- **Response**: Includes `state` field showing "PUBLISHED" or "IN_REVIEW"
- **Audit History**: Includes both `PUBLISHED` and `IN_REVIEW` versions

## Implementation Details

### Modified Files

1. **config/settings.py**: Added feature flag configuration
2. **cases/api_views.py**: Modified `CaseViewSet.get_queryset()` and `DocumentSourceViewSet.get_queryset()`
3. **cases/serializers.py**: Modified `CaseSerializer.__init__()` and `CaseDetailSerializer.get_audit_history()`
4. **.env.example**: Added feature flag documentation

### Logic Changes

- **CaseViewSet**: Filters by `state__in=[PUBLISHED, IN_REVIEW]` when flag is enabled
- **DocumentSourceViewSet**: Includes sources from IN_REVIEW cases when flag is enabled
- **CaseSerializer**: Dynamically adds `state` field to response when flag is enabled
- **Audit History**: Includes IN_REVIEW versions in audit trail when flag is enabled

## Deployment

For emergency deployment to expose IN_REVIEW cases:

1. Set environment variable: `EXPOSE_CASES_IN_REVIEW=True`
2. Restart the application
3. No database migrations required
4. No code deployment required (if already deployed)

To revert:

1. Set environment variable: `EXPOSE_CASES_IN_REVIEW=False`
2. Restart the application

## Testing

Test the feature flag behavior:

```bash
# Test with flag disabled
curl http://localhost:8000/api/cases/

# Enable flag in .env
echo "EXPOSE_CASES_IN_REVIEW=True" >> .env

# Restart server and test again
curl http://localhost:8000/api/cases/
# Should now include IN_REVIEW cases with state field
```
