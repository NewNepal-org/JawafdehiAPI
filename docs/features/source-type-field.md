# Source Type Field for Document Sources

## Overview

Added a `source_type` field to the DocumentSource model to categorize sources by their origin type. This enables better data analysis and filtering of sources.

## Backend Implementation

### 1. Model Changes

**File**: `cases/models.py`

Added `SourceType` enum with the following choices:
- `OFFICIAL_GOVERNMENT` - Official (Government)
- `MEDIA_NEWS` - Media/News
- `SOCIAL_MEDIA` - Social Media
- `INTERNAL_DOCUMENT` - Internal Document
- `ACADEMIC_RESEARCH` - Academic/Research
- `LEGAL_DOCUMENT` - Legal Document
- `WHISTLEBLOWER` - Whistleblower
- `OTHER` - Other (default)

Added `source_type` field to `DocumentSource` model:
```python
source_type = models.CharField(
    max_length=50,
    choices=SourceType.choices,
    default=SourceType.OTHER,
    help_text="Type of source"
)
```

### 2. Admin Interface Updates

**File**: `cases/admin.py`

- Added `source_type` to `list_display` for easy viewing in the admin list
- Added `source_type` to `list_filter` for filtering sources by type
- Added `source_type` to fieldsets in the "Basic Information" section
- Imported `SourceType` from models

The field appears as a dropdown (select) in the admin form.

### 3. API Updates

**File**: `cases/serializers.py`

Added `source_type` to the `DocumentSourceSerializer` fields list. The API now returns:

```json
{
  "id": 1,
  "source_id": "source:20260218:abc123",
  "title": "Example Source",
  "description": "Source description",
  "source_type": "MEDIA_NEWS",
  "url": ["https://example.com"],
  "related_entities": [...],
  "created_at": "2026-02-18T10:00:00Z",
  "updated_at": "2026-02-18T10:00:00Z"
}
```

### 4. Migration

**File**: `cases/migrations/0011_add_source_type_field.py`

Migration adds the `source_type` field with:
- Default value: `OTHER`
- All existing sources will be set to `OTHER` by default

**Command to generate migration**:
```bash
poetry run python manage.py makemigrations cases -n add_source_type_field
```

**Command to apply migration**:
```bash
poetry run python manage.py migrate
```

## Frontend Implementation Guide

### TypeScript Interface Updates

**File**: `src/types/documentSource.ts` (or equivalent)

Update the `DocumentSource` interface to include the new field:

```typescript
export enum SourceType {
  OFFICIAL_GOVERNMENT = 'OFFICIAL_GOVERNMENT',
  MEDIA_NEWS = 'MEDIA_NEWS',
  SOCIAL_MEDIA = 'SOCIAL_MEDIA',
  INTERNAL_DOCUMENT = 'INTERNAL_DOCUMENT',
  ACADEMIC_RESEARCH = 'ACADEMIC_RESEARCH',
  LEGAL_DOCUMENT = 'LEGAL_DOCUMENT',
  WHISTLEBLOWER = 'WHISTLEBLOWER',
  OTHER = 'OTHER',
}

export const SourceTypeLabels: Record<SourceType, string> = {
  [SourceType.OFFICIAL_GOVERNMENT]: 'Official (Government)',
  [SourceType.MEDIA_NEWS]: 'Media/News',
  [SourceType.SOCIAL_MEDIA]: 'Social Media',
  [SourceType.INTERNAL_DOCUMENT]: 'Internal Document',
  [SourceType.ACADEMIC_RESEARCH]: 'Academic/Research',
  [SourceType.LEGAL_DOCUMENT]: 'Legal Document',
  [SourceType.WHISTLEBLOWER]: 'Whistleblower',
  [SourceType.OTHER]: 'Other',
};

export interface DocumentSource {
  id: number;
  source_id: string;
  title: string;
  description: string;
  source_type: SourceType;  // NEW FIELD
  url: string[];
  related_entities: JawafEntity[];
  created_at: string;
  updated_at: string;
}
```

### Form Component Updates

**File**: `src/components/DocumentSourceForm.tsx` (or equivalent)

Add a dropdown/select field for source type:

```tsx
import { SourceType, SourceTypeLabels } from '@/types/documentSource';

// In your form component:
<FormField
  control={form.control}
  name="source_type"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Source Type</FormLabel>
      <Select
        onValueChange={field.onChange}
        defaultValue={field.value || SourceType.OTHER}
      >
        <FormControl>
          <SelectTrigger>
            <SelectValue placeholder="Select source type" />
          </SelectTrigger>
        </FormControl>
        <SelectContent>
          {Object.entries(SourceTypeLabels).map(([value, label]) => (
            <SelectItem key={value} value={value}>
              {label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <FormDescription>
        Categorize the source by its origin type
      </FormDescription>
      <FormMessage />
    </FormItem>
  )}
/>
```

### Display Component Updates

**File**: `src/components/DocumentSourceDetail.tsx` (or equivalent)

Display the source type in the detail view:

```tsx
import { SourceTypeLabels } from '@/types/documentSource';

// In your detail component:
<div className="source-type">
  <span className="label">Source Type:</span>
  <span className="value">
    {SourceTypeLabels[source.source_type]}
  </span>
</div>
```

### Filter Component Updates

If you have filtering functionality, add source type as a filter option:

```tsx
<Select
  value={filters.sourceType}
  onValueChange={(value) => setFilters({ ...filters, sourceType: value })}
>
  <SelectTrigger>
    <SelectValue placeholder="Filter by source type" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="all">All Types</SelectItem>
    {Object.entries(SourceTypeLabels).map(([value, label]) => (
      <SelectItem key={value} value={value}>
        {label}
      </SelectItem>
    ))}
  </SelectContent>
</Select>
```

## Usage

### Admin Interface

1. Navigate to Django Admin → Document sources
2. Create or edit a document source
3. Select the appropriate source type from the dropdown
4. The field defaults to "Other" if not specified

### API

The source type is included in all API responses for document sources:

**GET** `/api/sources/`
**GET** `/api/sources/{source_id}/`

Response includes `source_type` field with one of the enum values.

## Data Analysis Benefits

With this field, you can now:

1. **Filter sources by type** in the admin interface
2. **Analyze source distribution** - understand where information is coming from
3. **Quality assessment** - evaluate reliability based on source type
4. **Reporting** - generate statistics on source types used in cases
5. **Search and discovery** - find sources by category

## Example Queries

### Django ORM

```python
# Get all government sources
official_sources = DocumentSource.objects.filter(
    source_type=SourceType.OFFICIAL_GOVERNMENT
)

# Count sources by type
from django.db.models import Count
source_stats = DocumentSource.objects.values('source_type').annotate(
    count=Count('id')
)

# Get cases with media sources
cases_with_media = Case.objects.filter(
    evidence__source_id__in=DocumentSource.objects.filter(
        source_type=SourceType.MEDIA_NEWS
    ).values_list('source_id', flat=True)
).distinct()
```

### API Filtering (if implemented)

```
GET /api/sources/?source_type=MEDIA_NEWS
GET /api/sources/?source_type=OFFICIAL_GOVERNMENT
```

## Migration Notes

- All existing sources are set to `OTHER` by default
- Admins/Moderators should review and update source types for existing sources
- The field is required (has a default), so no null values

## Future Enhancements

Potential improvements:
1. Add source type statistics to the dashboard
2. Implement API filtering by source type
3. Add source type badges/icons in the UI
4. Create reports showing source type distribution per case
5. Add validation rules based on source type (e.g., government sources require official URLs)
