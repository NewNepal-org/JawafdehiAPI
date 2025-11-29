# Entity Migration Summary

## Overview
Successfully migrated the entity system from simple string IDs to a proper `JawafEntity` model with database relationships.

## Changes Made

### 1. New Model: `JawafEntity`
- **Location**: `cases/models.py`
- **Fields**:
  - `id`: Auto-incrementing primary key
  - `nes_id`: Unique string field for Nepal Entity Service IDs (nullable)
  - `display_name`: String field for custom entity names (nullable)
  - `created_at`, `updated_at`: Timestamps
- **Constraints**:
  - Must have either `nes_id` OR `display_name` (or both)
  - `nes_id` must be unique (excluding nulls)
  - Validates `nes_id` format using NES validator

### 2. Updated Models

#### Case Model
Changed from:
- `alleged_entities`: EntityListField (JSON list of strings)
- `related_entities`: EntityListField (JSON list of strings)
- `locations`: EntityListField (JSON list of strings)

To:
- `alleged_entities`: ManyToManyField to JawafEntity
- `related_entities`: ManyToManyField to JawafEntity
- `locations`: ManyToManyField to JawafEntity

#### DocumentSource Model
Changed from:
- `related_entity_ids`: EntityListField (JSON list of strings)

To:
- `related_entities`: ManyToManyField to JawafEntity

### 3. Admin Interface
- **Location**: `cases/admin.py`
- Added `JawafEntityAdmin` for managing entities
- Updated `CaseAdmin` to use `filter_horizontal` for entity selection
- Updated `DocumentSourceAdmin` to use `filter_horizontal` for entity selection
- Removed custom `MultiEntityIDField` widgets (now using Django's built-in M2M widgets)

### 4. API Serializers
- **Location**: `cases/serializers.py`
- Added `JawafEntitySerializer` with fields: `id`, `nes_id`, `display_name`
- Updated `CaseSerializer` to use nested `JawafEntitySerializer`
- Updated `DocumentSourceSerializer` to use nested `JawafEntitySerializer`

### 5. Migration
- **File**: `cases/migrations/0005_add_jawafentity_model.py`
- **Process**:
  1. Renamed old fields to preserve data
  2. Created `JawafEntity` model
  3. Added new ManyToMany fields
  4. Migrated data: converted entity ID strings to JawafEntity records (deduplicated by nes_id)
  5. Removed old fields

## Data Migration Details

The migration automatically:
- Extracted all unique entity IDs from existing Cases and DocumentSources
- Created JawafEntity records with `nes_id` set to the old entity ID string
- Deduplicated entities (same `nes_id` = same entity across all cases/sources)
- Linked Cases and DocumentSources to the new JawafEntity records

## Next Steps (Future Work)

### Admin UI Enhancement
Currently using Django's default filter_horizontal widget. Future improvements:
- Create custom popup form for entity selection/creation
- Add search functionality for existing entities
- Allow inline entity creation with NES ID or display name
- Add autocomplete for entity search

### Display Name Population
- Optionally fetch display names from NES API for entities with `nes_id`
- Cache display names in the `display_name` field for performance

## Testing

Verified:
- ✅ Migration runs successfully
- ✅ Existing entity IDs converted to JawafEntity records
- ✅ Entities deduplicated by nes_id
- ✅ Model validation works (requires nes_id or display_name)
- ✅ Django admin check passes with no issues

## Files Modified

1. `cases/models.py` - Added JawafEntity model, updated Case and DocumentSource
2. `cases/admin.py` - Added JawafEntityAdmin, updated form widgets
3. `cases/serializers.py` - Added JawafEntitySerializer, updated API responses
4. `cases/fields.py` - Removed EntityListField (no longer needed)
5. `cases/widgets.py` - Removed MultiEntityIDField (no longer needed)
6. `cases/migrations/0005_add_jawafentity_model.py` - Data migration script
