# Migration Fix: URL Field to JSONField Conversion

## Problem

When running `poetry run python manage.py migrate`, the migration `0010_change_url_to_jsonfield` was failing with:

```
django.db.utils.IntegrityError: CHECK constraint failed: (JSON_VALID("url") OR "url" IS NULL)
```

## Root Cause

The migration was attempting to change the `url` field from `URLField` (string) to `JSONField` (list) in a single step. However, SQLite enforces a CHECK constraint that validates JSON data. The existing string data in the database was not valid JSON, causing the constraint to fail.

The original migration had the operations in the wrong order:
1. ❌ `AlterField` - Change field type to JSONField
2. ❌ `RunPython` - Convert data to list format

This meant Django was trying to change the field type BEFORE converting the data, which failed because the existing string data wasn't valid JSON.

## Solution

The migration was fixed to perform operations in the correct order:

1. ✅ `RunPython` - Convert existing string data to JSON format (while still URLField)
2. ✅ `AlterField` - Change field type to JSONField (data is already in JSON format)

### Updated Migration Code

**File**: `cases/migrations/0010_change_url_to_jsonfield.py`

```python
def migrate_urls_to_list(apps, schema_editor):
    """
    Convert existing single URL strings to JSON lists.
    This runs BEFORE the field type change to ensure data compatibility.
    """
    DocumentSource = apps.get_model('cases', 'DocumentSource')
    db_alias = schema_editor.connection.alias
    
    for source in DocumentSource.objects.using(db_alias).all():
        url_value = source.url
        
        if url_value is None or url_value == '':
            # Convert None or empty string to empty list JSON
            source.url = '[]'
        elif isinstance(url_value, str):
            if url_value.startswith('['):
                continue  # Already in list format
            else:
                # Convert single URL string to JSON list
                import json
                source.url = json.dumps([url_value])
        
        source.save(update_fields=['url'])


def reverse_urls_to_string(apps, schema_editor):
    """
    Convert URL lists back to single strings (for rollback).
    Takes the first URL from the list, or sets to None if empty.
    """
    DocumentSource = apps.get_model('cases', 'DocumentSource')
    db_alias = schema_editor.connection.alias
    
    for source in DocumentSource.objects.using(db_alias).all():
        import json
        
        try:
            if isinstance(source.url, str):
                url_list = json.loads(source.url)
            elif isinstance(source.url, list):
                url_list = source.url
            else:
                url_list = []
            
            source.url = url_list[0] if url_list else None
            source.save(update_fields=['url'])
        except (json.JSONDecodeError, TypeError, IndexError):
            source.url = None
            source.save(update_fields=['url'])


class Migration(migrations.Migration):
    dependencies = [
        ('cases', '0009_merge_20260112_0309'),
    ]

    operations = [
        # Step 1: Convert data to JSON format (while still URLField)
        migrations.RunPython(migrate_urls_to_list, reverse_urls_to_string),
        
        # Step 2: Change field type to JSONField
        migrations.AlterField(
            model_name='documentsource',
            name='url',
            field=models.JSONField(blank=True, default=list, help_text='List of URLs for this source'),
        ),
    ]
```

## Key Changes

### 1. Data Conversion Logic

The `migrate_urls_to_list` function now:
- Converts string URLs to JSON array format: `"https://example.com"` → `'["https://example.com"]'`
- Handles empty strings and None values: `""` or `None` → `'[]'`
- Stores data as JSON string (valid for URLField) before the field type change
- Uses `json.dumps()` to ensure proper JSON formatting

### 2. Reverse Migration

The `reverse_urls_to_string` function:
- Parses JSON lists back to Python lists
- Takes the first URL from the list
- Sets to None if the list is empty
- Handles errors gracefully

### 3. Operation Order

```python
operations = [
    # FIRST: Convert data while field is still URLField
    migrations.RunPython(migrate_urls_to_list, reverse_urls_to_string),
    
    # SECOND: Change field type to JSONField
    migrations.AlterField(...),
]
```

## How to Apply

If you encounter this error, follow these steps:

### 1. Check Current Migration Status

```bash
poetry run python manage.py showmigrations cases
```

### 2. Rollback to Before the Problematic Migration (if needed)

```bash
poetry run python manage.py migrate cases 0009
```

### 3. Apply the Fixed Migration

```bash
poetry run python manage.py migrate cases
```

### 4. Verify Data Conversion

```bash
poetry run python manage.py shell -c "from cases.models import DocumentSource; [print(f'Source {s.id}: {s.url}') for s in DocumentSource.objects.all()]"
```

Expected output:
```
Source 1: ['https://example.com']
Source 2: []
```

## Testing

Run the test suite to verify everything works:

```bash
poetry run pytest tests/test_source_type_field.py -v
```

All tests should pass:
```
7 passed, 2 warnings in 0.92s
```

## Verification

After applying the migration, verify:

1. **Data Format**: URLs are stored as lists
   ```python
   source = DocumentSource.objects.first()
   print(type(source.url))  # <class 'list'>
   ```

2. **Admin Interface**: Multi-URL widget works correctly
   - Navigate to `/admin/cases/documentsource/add/`
   - Add multiple URLs using the "+ Add URL" button
   - Save and verify

3. **API Response**: URLs returned as arrays
   ```json
   {
     "url": ["https://example.com", "https://backup.com"]
   }
   ```

## Why This Approach Works

### SQLite Constraints

SQLite enforces JSON validation through CHECK constraints. When you define a JSONField, SQLite adds:
```sql
CHECK (JSON_VALID("url") OR "url" IS NULL)
```

This constraint is checked during the `ALTER TABLE` operation. If existing data isn't valid JSON, the migration fails.

### Two-Step Process

By converting data to JSON format BEFORE changing the field type:
1. Data is converted to valid JSON strings (e.g., `'["url"]'`)
2. These strings are valid for URLField (max_length=2000)
3. When AlterField runs, all data is already valid JSON
4. SQLite's CHECK constraint passes
5. Django then interprets the JSON strings as Python lists

## Rollback

If you need to rollback:

```bash
# Rollback to before URL field change
poetry run python manage.py migrate cases 0009
```

The reverse function will:
- Convert lists back to single strings
- Take the first URL from each list
- Set to None if list is empty

## Related Files

- `cases/models.py` - DocumentSource model with JSONField
- `cases/widgets.py` - MultiURLField widget
- `cases/admin.py` - Admin form with multi-URL support
- `cases/migrations/0010_change_url_to_jsonfield.py` - Fixed migration
- `cases/migrations/0011_add_source_type_field.py` - Source type field

## Lessons Learned

1. **Order Matters**: Data conversion must happen BEFORE field type changes
2. **JSON Validation**: SQLite enforces JSON validity through CHECK constraints
3. **Test Migrations**: Always test migrations with existing data
4. **Provide Rollback**: Include reverse functions for all data migrations
5. **Handle Edge Cases**: Account for None, empty strings, and existing JSON data

## Status

✅ **FIXED** - Migration now runs successfully with existing data
✅ **TESTED** - All tests passing
✅ **VERIFIED** - Data correctly converted to list format
✅ **DOCUMENTED** - Complete fix documentation provided

---

**Fix Date**: February 19, 2026
**Issue**: IntegrityError during URL field migration
**Resolution**: Reordered migration operations to convert data before field type change
