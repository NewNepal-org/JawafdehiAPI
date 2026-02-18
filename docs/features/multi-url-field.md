# Multi-URL Field for Document Sources

## Overview

Added support for multiple URLs in DocumentSource model, allowing contributors to add multiple source URLs instead of just one.

## Changes Made

### 1. Model Changes
- **File**: `cases/models.py`
- Changed `DocumentSource.url` from `URLField` to `JSONField` storing a list of URLs
- Migration: `0010_change_url_to_jsonfield.py` with data migration to convert existing single URLs to lists

### 2. Widget Implementation
- **Files**: 
  - `cases/widgets.py` - Added `MultiURLWidget` and `MultiURLField`
  - `cases/templates/cases/widgets/multi_url_widget.html` - Template for the widget
  - `cases/static/cases/css/widgets.css` - Added `.url-input` styles
  - `cases/static/cases/js/widgets.js` - Added `url` configuration

### 3. Admin Form Updates
- **File**: `cases/admin.py`
- Updated `DocumentSourceAdminForm` to use `MultiURLField` instead of single `URLField`
- Imported `MultiURLField` from widgets

## Features

- **Add Multiple URLs**: Green "+ Add URL" button to add new URL fields
- **Remove URLs**: Red "×" button on each URL field to remove it
- **Drag & Drop**: Reorder URLs by dragging the handle (⋮⋮)
- **Validation**: Each URL is validated using Django's URLValidator
- **Responsive**: URL inputs are full-width (600px) for better usability

## Usage

1. Navigate to Django Admin → Document sources
2. Create or edit a document source
3. In the "URLs" field, you'll see:
   - Existing URLs (if any) with remove buttons
   - "+ Add URL" button to add more URLs
4. Click "+ Add URL" to add a new URL field
5. Enter the URL (e.g., `https://example.com`)
6. Click the red "×" button to remove a URL
7. Drag the "⋮⋮" handle to reorder URLs
8. Save the form

## Data Structure

URLs are stored as a JSON array in the database:

```json
["https://example.com", "https://another-source.com"]
```

## API Response

The API returns URLs as an array:

```json
{
  "source_id": "source:20260218:abc123",
  "title": "Example Source",
  "url": [
    "https://example.com",
    "https://another-source.com"
  ],
  ...
}
```

## Migration

The migration automatically converts existing data:
- Single URL string → List with one URL
- `null` → Empty list `[]`
- Empty string → Empty list `[]`

## Rollback

If needed, the migration can be rolled back:
```bash
poetry run python manage.py migrate cases 0009
```

This will convert URL lists back to single strings (taking the first URL from each list).
