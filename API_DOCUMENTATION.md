# Jawafdehi API Documentation

This document explains how to access and use the OpenAPI documentation for the Jawafdehi Public Accountability API.

## Accessing the API Documentation

The API documentation is available through multiple endpoints:

### 1. Swagger UI (Interactive Documentation)

**URL:** `http://localhost:8000/api/swagger/`

The Swagger UI provides an interactive interface where you can:
- Browse all available endpoints
- View request/response schemas
- Try out API calls directly from the browser
- See example requests and responses

### 2. OpenAPI Schema (YAML)

**URL:** `http://localhost:8000/api/schema/`

This endpoint returns the complete OpenAPI 3.0 schema in YAML format. You can:
- Download the schema for use with API clients
- Import into tools like Postman or Insomnia
- Generate client libraries using OpenAPI generators

### 3. Generate Schema File

You can also generate the schema as a file using the Django management command:

```bash
python manage.py spectacular --color --file schema.yml
```

## API Overview

The Jawafdehi API provides read-only access to published accountability cases and document sources.

### Key Features

- **Public Access**: No authentication required
- **Published Cases Only**: Only cases with state=PUBLISHED are accessible
- **Filtering & Search**: Filter by case type and tags, search across multiple fields
- **Pagination**: Results are paginated with 20 items per page
- **Audit History**: View complete version history for published cases

## Available Endpoints

### Cases

#### List Cases
```
GET /api/cases/
```

**Query Parameters:**
- `case_type`: Filter by case type (CORRUPTION or PROMISES)
- `tags`: Filter cases containing a specific tag
- `search`: Full-text search across title, description, and key allegations
- `page`: Page number for pagination

**Example:**
```bash
curl "http://localhost:8000/api/cases/?case_type=CORRUPTION&page=1"
```

#### Retrieve Case
```
GET /api/cases/{id}/
```

Returns detailed information about a specific case, including:
- Complete case data
- Evidence and timeline
- Audit history (all published versions)

**Example:**
```bash
curl "http://localhost:8000/api/cases/1/"
```

### Document Sources

#### List Sources
```
GET /api/sources/
```

Returns sources associated with published cases.

**Query Parameters:**
- `page`: Page number for pagination

**Example:**
```bash
curl "http://localhost:8000/api/sources/"
```

#### Retrieve Source
```
GET /api/sources/{id}/
```

Returns detailed information about a specific document source.

**Example:**
```bash
curl "http://localhost:8000/api/sources/1/"
```

## Response Format

All responses are in JSON format with the following structure:

### Paginated List Response
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/cases/?page=2",
  "previous": null,
  "results": [...]
}
```

### Case Object
```json
{
  "id": 1,
  "case_id": "case-abc123def456",
  "case_type": "CORRUPTION",
  "title": "Case Title",
  "case_start_date": "2024-01-15",
  "case_end_date": null,
  "alleged_entities": [
    "entity:person/john-doe",
    "entity:organization/government/ministry-of-finance"
  ],
  "related_entities": [],
  "locations": [
    "entity:location/district/kathmandu"
  ],
  "tags": ["land-encroachment", "national-interest"],
  "description": "Detailed description...",
  "key_allegations": [
    "Allegation statement 1",
    "Allegation statement 2"
  ],
  "timeline": [
    {
      "date": "2024-01-15",
      "title": "Event title",
      "description": "Event description"
    }
  ],
  "evidence": [
    {
      "source_id": "source:20240115:abc123",
      "description": "Description of evidence"
    }
  ],
  "versionInfo": {
    "version_number": 1,
    "action": "published",
    "datetime": "2024-01-15T10:30:00Z"
  },
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Document Source Object
```json
{
  "id": 1,
  "source_id": "source:20240115:abc123",
  "title": "Source Title",
  "description": "Source description",
  "url": "https://example.com/document.pdf",
  "related_entity_ids": [
    "entity:person/john-doe"
  ],
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

## Entity ID Format

Entity IDs follow the Nepal Entity Service (NES) format:

- **Persons**: `entity:person/{slug}`
- **Organizations**: `entity:organization/{type}/{slug}`
- **Locations**: `entity:location/{type}/{slug}`

Examples:
- `entity:person/rabi-lamichhane`
- `entity:organization/government/nepal-government`
- `entity:organization/political_party/rastriya-swatantra-party`
- `entity:location/district/kathmandu`
- `entity:location/region/kathmandu-valley`

## Error Responses

The API returns standard HTTP status codes:

- `200 OK`: Successful request
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a message:
```json
{
  "detail": "Not found."
}
```

## Rate Limiting

Currently, there are no rate limits on the public API. This may change in production.

## CORS

The API allows cross-origin requests from all origins for GET, HEAD, and OPTIONS methods.

## Development vs Production

### Development
- Base URL: `http://localhost:8000`
- Debug mode enabled
- CORS allows all origins

### Production
- Base URL: TBD
- Debug mode disabled
- CORS restricted to specific domains
- HTTPS required

## Testing the API

### Using curl
```bash
# List cases
curl "http://localhost:8000/api/cases/"

# Search cases
curl "http://localhost:8000/api/cases/?search=corruption"

# Filter by case type
curl "http://localhost:8000/api/cases/?case_type=CORRUPTION"

# Get specific case
curl "http://localhost:8000/api/cases/1/"
```

### Using Python
```python
import requests

# List cases
response = requests.get('http://localhost:8000/api/cases/')
cases = response.json()

# Search cases
response = requests.get('http://localhost:8000/api/cases/', params={
    'search': 'corruption',
    'case_type': 'CORRUPTION'
})
results = response.json()['results']

# Get specific case
response = requests.get('http://localhost:8000/api/cases/1/')
case = response.json()
```

### Using JavaScript
```javascript
// List cases
fetch('http://localhost:8000/api/cases/')
  .then(response => response.json())
  .then(data => console.log(data));

// Search cases
fetch('http://localhost:8000/api/cases/?search=corruption&case_type=CORRUPTION')
  .then(response => response.json())
  .then(data => console.log(data.results));

// Get specific case
fetch('http://localhost:8000/api/cases/1/')
  .then(response => response.json())
  .then(case => console.log(case));
```

## Support

For questions or issues with the API, please contact the development team or file an issue in the project repository.
