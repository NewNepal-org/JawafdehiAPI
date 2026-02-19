# Source Type Field - Quick Reference

## Source Type Values

| Value | Display Label | Use Case |
|-------|---------------|----------|
| `OFFICIAL_GOVERNMENT` | Official (Government) | Government reports, official documents, audit findings |
| `MEDIA_NEWS` | Media/News | News articles, press releases, media reports |
| `SOCIAL_MEDIA` | Social Media | Twitter/X posts, Facebook posts, social media content |
| `INTERNAL_DOCUMENT` | Internal Document | Internal memos, leaked documents, internal communications |
| `ACADEMIC_RESEARCH` | Academic/Research | Research papers, academic studies, scholarly articles |
| `LEGAL_DOCUMENT` | Legal Document | Court documents, legal filings, judgments |
| `WHISTLEBLOWER` | Whistleblower | Whistleblower reports, anonymous tips |
| `OTHER` | Other | Any other source type (default) |

## Django Admin Usage

### Creating a New Source
1. Go to Admin → Document sources → Add document source
2. Fill in required fields (Title, Description)
3. Select appropriate Source Type from dropdown
4. If unsure, leave as "Other" (default)
5. Save

### Filtering Sources
1. Go to Admin → Document sources
2. Use "Source type" filter in right sidebar
3. Click on desired type to filter

### Bulk Operations
```python
# In Django shell
from cases.models import DocumentSource, SourceType

# Update multiple sources
DocumentSource.objects.filter(
    title__icontains="audit"
).update(source_type=SourceType.OFFICIAL_GOVERNMENT)
```

## API Usage

### Response Format
```json
{
  "source_type": "MEDIA_NEWS"
}
```

### Filtering (if implemented)
```bash
GET /api/sources/?source_type=OFFICIAL_GOVERNMENT
GET /api/sources/?source_type=MEDIA_NEWS
```

## Python Code Examples

### Creating a Source
```python
from cases.models import DocumentSource, SourceType

source = DocumentSource.objects.create(
    title="Government Audit Report 2024",
    description="Annual audit findings",
    source_type=SourceType.OFFICIAL_GOVERNMENT,
    url=["https://oag.gov.np/reports/2024.pdf"]
)
```

### Querying by Type
```python
# Get all government sources
gov_sources = DocumentSource.objects.filter(
    source_type=SourceType.OFFICIAL_GOVERNMENT
)

# Get all media sources
media_sources = DocumentSource.objects.filter(
    source_type=SourceType.MEDIA_NEWS
)

# Exclude "Other" category
categorized = DocumentSource.objects.exclude(
    source_type=SourceType.OTHER
)
```

### Statistics
```python
from django.db.models import Count

# Count by type
stats = DocumentSource.objects.values('source_type').annotate(
    count=Count('id')
).order_by('-count')

for item in stats:
    print(f"{item['source_type']}: {item['count']}")
```

### Display Label
```python
source = DocumentSource.objects.first()
print(source.source_type)  # "MEDIA_NEWS"
print(source.get_source_type_display())  # "Media/News"
```

## Frontend TypeScript

### Enum Definition
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
```

### Labels
```typescript
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
```

### Display
```typescript
// Get label
const label = SourceTypeLabels[source.source_type];

// Render
<span>{SourceTypeLabels[source.source_type]}</span>
```

## Testing

### Run Tests
```bash
poetry run pytest tests/test_source_type_field.py -v
```

### Test Coverage
- ✅ Default value
- ✅ All choices
- ✅ Display labels
- ✅ Filtering
- ✅ Serialization
- ✅ Updates
- ✅ Statistics

## Common Tasks

### Update Existing Sources
```python
# Update sources with "audit" in title
DocumentSource.objects.filter(
    title__icontains="audit"
).update(source_type=SourceType.OFFICIAL_GOVERNMENT)

# Update sources with news domains
DocumentSource.objects.filter(
    url__icontains="news"
).update(source_type=SourceType.MEDIA_NEWS)
```

### Generate Report
```python
from django.db.models import Count
from cases.models import DocumentSource, SourceType

# Source distribution
for choice in SourceType.choices:
    count = DocumentSource.objects.filter(
        source_type=choice[0]
    ).count()
    print(f"{choice[1]}: {count}")
```

### Validation
```python
# Check for uncategorized sources
uncategorized = DocumentSource.objects.filter(
    source_type=SourceType.OTHER
).count()
print(f"Uncategorized sources: {uncategorized}")
```

## Migration Commands

```bash
# Generate migration
poetry run python manage.py makemigrations cases -n add_source_type_field

# Apply migration
poetry run python manage.py migrate

# Rollback (if needed)
poetry run python manage.py migrate cases 0010
```

## Troubleshooting

### Issue: Source type not showing in admin
**Solution**: Clear browser cache and refresh

### Issue: API not returning source_type
**Solution**: Check serializer includes 'source_type' in fields list

### Issue: Invalid choice error
**Solution**: Use SourceType enum values, not display labels

### Issue: Migration fails
**Solution**: Check for existing migrations, resolve conflicts

## Best Practices

1. **Always use enum values**, not strings:
   ```python
   # Good
   source_type=SourceType.MEDIA_NEWS
   
   # Bad
   source_type="MEDIA_NEWS"
   ```

2. **Use display labels for UI**:
   ```python
   # Good
   label = source.get_source_type_display()
   
   # Bad
   label = source.source_type
   ```

3. **Default to OTHER when uncertain**:
   - Better to categorize as OTHER than guess incorrectly
   - Can be updated later when more information is available

4. **Review and update regularly**:
   - Periodically review sources marked as OTHER
   - Update to appropriate categories as information becomes available

## Support

For questions or issues:
1. Check `docs/features/source-type-field.md` for detailed documentation
2. Review test cases in `tests/test_source_type_field.py`
3. Consult `IMPLEMENTATION_SUMMARY_SOURCE_TYPE.md` for implementation details
