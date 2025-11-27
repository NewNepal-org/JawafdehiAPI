# Design Document

## Overview

The Jawafdehi platform implements a role-based accountability system with a draft-review-publish workflow. The architecture follows Django's MVT (Model-View-Template) pattern with Django REST Framework for API endpoints. The system uses a revision-based approach to track all changes to cases while maintaining clear separation between draft work and published content.

The platform supports three user roles with distinct permissions:
- **Contributors**: Create and edit assigned cases, limited to Draft/In Review states
- **Moderators**: Review and publish all cases, manage contributors
- **Admins**: Full system access including moderator management

## Architecture

### Technology Stack

- **Backend Framework**: Django
- **API Framework**: Django REST Framework with drf-spectacular for OpenAPI documentation
- **Database**: PostgreSQL (via dj-database-url)
- **Authentication**: Django's built-in auth with django-rules for object-level permissions
- **Admin Interface**: Jazzmin (Bootstrap 4-based admin theme)
- **Rich Text**: TinyMCE for description fields

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Public Interface                      │
│  (Browse/View Published Cases, API Access)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (DRF)                         │
│  - CaseViewSet (filtering, search, pagination)              │
│  - DocumentSourceViewSet                                     │
│  - Permission Classes (role-based access control)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│  - State transition validation                               │
│  - Assignment-based access control                           │
│  - Revision creation on save                                 │
│  - Entity ID validation (NES integration)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer (Models)                     │
│  - Case (core case data with versioning)                    │
│  - DocumentSource (evidence sources)                         │
│  - User + Groups (Django auth)                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Models

#### Case Model
The core model representing a case of alleged misconduct.

**Fields:**
- `case_id`: CharField - unique identifier for the case (shared across versions)
- `version`: IntegerField (default=1) - version number, increments with each published update
- `case_type`: Enum (CORRUPTION, PROMISES)
- `state`: Enum (DRAFT, IN_REVIEW, PUBLISHED, CLOSED)
- `title`: CharField(200)
- `case_start_date`: DateField (optional)
- `case_end_date`: DateField (optional)
- `alleged_entities`: Custom EntityListField (list of entity ID strings)
- `related_entities`: Custom EntityListField (list of entity ID strings)
- `locations`: Custom EntityListField (list of location entity ID strings)
- `tags`: Custom TextListField (list of tag strings for categorization)
- `description`: TextField (rich text)
- `key_allegations`: Custom TextListField (list of allegation statement strings)
- `timeline`: Custom TimelineListField (list of TimelineEntry objects with date, title, description)
- `evidence`: Custom EvidenceListField (list of Evidence objects with source_id, description)
- `contributors`: ManyToManyField(User) - assignment relationship (not exposed in API)
- `versionInfo`: JSONField - tracks version metadata {version_number, user_id, change_summary, datetime}

**Custom Field Types:**
- `EntityListField`: Validates and stores list of entity IDs (for alleged_entities, related_entities, and locations)
- `TextListField`: Stores list of text strings (for key_allegations and tags)
- `TimelineListField`: Stores list of timeline entries with structured validation
- `EvidenceListField`: Stores list of evidence entries with source_id validation

**Methods:**
- `validate()`: Validates entity IDs, key allegations, timeline structure, evidence structure
- `create_draft()`: Creates a new draft version with the same case_id, incremented version, and state=DRAFT
- `publish()`: Publishes a draft by setting state=PUBLISHED

**Note on Versioning:**
The Case model stores all versions (drafts and published) in the same table. Each case has a unique `case_id` that remains constant across versions. The `version` field increments when creating a draft from a published case. Draft versions have `state=DRAFT` and share the same `case_id` as their published counterpart. When a draft is published, its state changes to PUBLISHED.

**Note on Deletion:**
Cases are soft-deleted by setting `state=CLOSED`. Hard deletion is not allowed to preserve audit history.

#### DocumentSource Model
Represents evidence sources that can be referenced by cases.

**Fields:**
- `source_id`: CharField - unique identifier for the source
- `title`: CharField(300)
- `description`: TextField
- `url`: URLField (optional)
- `related_entity_ids`: Custom EntityListField (list of entity IDs)
- `contributors`: ManyToManyField(User) - contributors assigned to manage this source
- `is_deleted`: BooleanField (default=False) - soft deletion flag

**Methods:**
- `validate()`: Validates entity IDs

**Note on Public Access:**
A DocumentSource is accessible to the public if it is referenced in the evidence field of at least one published case (state=PUBLISHED). Sources can be referenced by multiple cases through their evidence fields.

**Note on Access Control:**
Contributors can only view and edit sources they are assigned to via the `contributors` field. Moderators and Admins can manage all sources. When a contributor creates a source, they are automatically assigned as a contributor.

**Note on Deletion:**
Sources are soft-deleted by setting `is_deleted=True`. Hard deletion is not allowed.

### API ViewSets

#### CaseViewSet
Provides CRUD operations for cases with role-based filtering.

**Endpoints:**
- `GET /api/cases/` - List published cases (public, no authentication required)
- `GET /api/cases/{id}/` - Retrieve single published case with audit history (versionInfo from all published versions with same case_id)

**Filtering:**
- `case_type`: Filter by type
- `tags`: Filter by tags
- Search: Full-text search across title, description, key_allegations

**Serializer Fields:**
All Case fields except `contributors`, `state`, and `version` are exposed in the API. Only published cases (state=PUBLISHED, highest version per case_id) are accessible.

**Access Control:**
- API is public and read-only (no authentication required)
- All case management (create, update, delete, state transitions) is done through Django Admin
- Only published cases are visible through the API

#### DocumentSourceViewSet
Manages evidence sources.

**Endpoints:**
- `GET /api/sources/` - List sources associated with published cases (public, no authentication required)
- `GET /api/sources/{id}/` - Retrieve single source if associated with at least one published case

**Access Control:**
- API is public and read-only (no authentication required)
- All source management (create, update, delete) is done through Django Admin
- Only sources associated with published cases are visible through the API

### Django Admin Interface

All case and source management is done through the Django Admin interface with role-based permissions:

#### Admin Permissions
- **Admins**: Full access to all cases, sources, and user management
- **Moderators**: Can manage cases, sources, and contributors
- **Contributors**: Can create and edit assigned cases only

#### Admin Features
- Custom forms with rich text editor for descriptions
- Inline editing of evidence and timeline entries
- Contributor assignment interface
- State transition controls with validation
- Version history display
- Audit trail via versionInfo

## Data Models

### Entity Relationships

```
User (Django Auth)
  │
  ├─── ManyToMany ───> Case (via contributors)
  └─── ManyToMany ───> DocumentSource (via contributors)

Case
  │
  └─── ManyToMany ───> User (contributors)
  
Note: Multiple Case records can share the same case_id (different versions/drafts)
Note: Cases reference DocumentSources through the evidence field (EvidenceListField), not via ForeignKey

DocumentSource
  └─── ManyToMany ───> User (contributors)
```

### State Machine

```
[Draft v1] ──submit──> [In Review v1] ──approve──> [Published v1]
   ▲                        │                            │
   │                        │                            │
   └────revert──────────────┘                            │
                                                         │
                                              edit creates new
                                              draft case record
                                              (same case_id, state=DRAFT)
                                                         │
                                                         ▼
                                              [Draft] (same case_id)
                                                         │
                                                         │
                                              ──submit──> [In Review]
                                                         │
                                              ──approve──> [Published v2]
                                                          (version incremented)
```

**State Transition Rules:**
- Contributors: Can only transition between Draft ↔ In Review
- Moderators/Admins: Can transition to any state including Published and Closed
- Editing a Published case creates a new Case record with same `case_id` and `state=DRAFT`
- Approving a draft sets `state=PUBLISHED` and increments `version`
- Only one published version per case_id should be active at a time (state=PUBLISHED with highest version)

### Custom List Field Structures

#### EntityListField (alleged_entities / related_entities / locations)
Stores and validates a list of entity ID strings.
```python
# alleged_entities / related_entities example (persons and organizations)
[
  "entity:person/rabi-lamichhane",
  "entity:person/kp-sharma-oli",
  "entity:organization/government/nepal-government",
  "entity:organization/political_party/rastriya-swatantra-party"
]

# locations example (location entity IDs)
[
  "entity:location/district/kathmandu",
  "entity:location/district/chitwan",
  "entity:location/region/kathmandu-valley",
  "entity:location/country/nepal"
]
```

#### TextListField (key_allegations, tags)
Stores a list of text strings.
```python
# key_allegations example
[
  "Allegation statement 1",
  "Allegation statement 2"
]

# tags example
["land-encroaachment", "national-interest"]
```

#### TimelineListField (timeline)
Stores a list of timeline entry objects with validation.
```python
[
  {
    "date": "2024-01-15",
    "title": "Event title",
    "description": "Event description"
  }
]
```

#### EvidenceListField (evidence)
Stores a list of evidence entry objects with source_id validation.
```python
[
  {
    "source_id": "source:20240115:abc123",
    "description": "Description of how this source supports the case"
  }
]
```

**Implementation Note:** These custom fields will internally use JSONField for storage but provide structured validation and a cleaner API. Each field type will have its own validation logic to ensure data integrity.

### Version Info Structure

Both Case and DocumentSource models include a `versionInfo` JSONField that tracks metadata about each version:

```python
{
  "version_number": 2,
  "user_id": "user123",
  "change_summary": "Updated key allegations and added new evidence",
  "datetime": "2024-01-15T10:30:00Z"
}
```

This field is automatically populated when creating drafts or publishing versions, providing an audit trail of who made changes, when, and why.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Property 1: New cases start in Draft state
*For any* case created by a Contributor, the initial state should be Draft
**Validates: Requirements 1.1**

Property 2: Draft validation is lenient, In Review validation is strict
*For any* case in DRAFT state, only title uniqueness is required; other fields can be incomplete. *For any* case transitioning to IN_REVIEW state, all required fields (alleged_entities, key_allegations) must be valid and complete
**Validates: Requirements 1.2**

Property 3: Draft submission transitions to In Review
*For any* case in Draft state, when a Contributor submits it, the state should change to In Review
**Validates: Requirements 1.3**

Property 3a: Draft creation increments version
*For any* published case, when create_draft() is called, the new draft should have version incremented by 1
**Validates: Requirements 1.4**

Property 4: Editing published cases preserves original
*For any* published case, when a Contributor edits it, a new draft revision should be created and the published version should remain unchanged
**Validates: Requirements 1.4**

Property 5: Contributors can only transition between Draft and In Review
*For any* case assigned to a Contributor, that Contributor should only be able to change state between Draft and In Review, and attempts to change to Published or Closed should be rejected
**Validates: Requirements 1.5**

Property 6: Moderators can publish and close cases
*For any* case in In Review state, a Moderator should be able to change the state to Published or Closed
**Validates: Requirements 2.1**

Property 7: Approved revisions become the published version
*For any* case revision, when a Moderator approves it as Published, that revision's content should become the live public version
**Validates: Requirements 2.2**

Property 8: Public API only shows published cases
*For any* API request to list or retrieve cases, only cases with state=PUBLISHED and the highest version per case_id should be returned
**Validates: Requirements 6.1, 8.3**

Property 9: State transitions to IN_REVIEW, PUBLISHED, or CLOSED update versionInfo
*For any* case transitioning to IN_REVIEW, PUBLISHED, or CLOSED state, the versionInfo should be updated with the change details including user, timestamp, and change summary
**Validates: Requirements 2.4, 7.2**

Property 10: Evidence requires valid source references
*For any* evidence added to a case, it should include a source_id and description, and the source_id should reference an existing DocumentSource
**Validates: Requirements 4.1**

Property 11: Source validation enforces required fields
*For any* DocumentSource creation attempt missing title, or description, the Platform should reject the operation
**Validates: Requirements 4.2**

Property 12: Admin role-based permissions in Django Admin
*For any* user with Admin role in Django Admin, they should have full access to all cases, sources, and user management
**Validates: Requirements 5.1**

Property 13: Contributor assignment restricts access in Django Admin
*For any* user with Contributor role in Django Admin, they should only access cases they are assigned to
**Validates: Requirements 5.2, 3.1, 3.2**

Property 14: Moderators cannot manage other Moderators in Django Admin
*For any* Moderator user in Django Admin, attempts to create, edit, or delete other Moderator accounts should be rejected
**Validates: Requirements 5.3**

Property 15: Search and filter functionality
*For any* search query or filter parameters on the public API, the Platform should return published cases matching the criteria across title, description, key_allegations, tags, and case_type fields
**Validates: Requirements 6.2, 8.1**

Property 16: Published cases display complete data
*For any* published case retrieved via the public API, all associated evidence, sources, and timeline entries should be included
**Validates: Requirements 6.3**

Property 17: Editing published cases creates draft records
*For any* published case edited in Django Admin, a new Case record should be created with the same case_id, incremented version, and state=DRAFT
**Validates: Requirements 7.1**

Property 18: Soft delete sets state to CLOSED
*For any* case deleted in Django Admin, its state should be set to CLOSED and the record should remain in the database
**Validates: Requirements 7.3**

## Error Handling

### Validation Errors

**Entity ID Validation:**
- Invalid entity ID format → HTTP 400 with error message specifying invalid entity IDs
- Empty alleged_entities list → HTTP 400 with "At least one alleged entity is required"

**Case Validation:**
- Empty key_allegations → HTTP 400 with "At least one key allegation is required"
- Invalid timeline structure → HTTP 400 with specific field error
- Invalid evidence structure → HTTP 400 with specific field error

**Source Validation:**
- Missing required fields → HTTP 400 with field-specific errors
- Invalid source_id reference in evidence → HTTP 400 with "Source not found"

### Permission Errors

**Access Denied:**
- Contributor accessing unassigned case → HTTP 403 with "You do not have permission to access this case"
- Contributor attempting to publish → HTTP 403 with "Only moderators can publish cases"
- Moderator attempting to manage other moderators → HTTP 403 with "Insufficient permissions"

**Authentication Required:**
- Unauthenticated user attempting to create/edit → HTTP 401 with "Authentication required"

### State Transition Errors

**Invalid State Transitions:**
- Contributor attempting to transition to Published/Closed → HTTP 400 with "Invalid state transition"
- Attempting to edit non-existent case → HTTP 404 with "Case not found"

### Database Errors

**Integrity Errors:**
- Duplicate source_id → HTTP 400 with "Source ID already exists"
- Foreign key violations → HTTP 400 with appropriate error message

**Connection Errors:**
- Database unavailable → HTTP 503 with "Service temporarily unavailable"

## Testing Strategy

**Development Approach:** The platform will follow Test-Driven Development (TDD). Tests should be written before implementing features, ensuring that all functionality is testable and meets requirements from the start.

### Unit Testing

The platform will use Django's built-in testing framework (`django.test.TestCase`) for unit tests.

**Test Coverage Areas:**
- Model validation logic (clean methods)
- Model save behavior (revision creation)
- Permission class logic
- Serializer validation
- Custom admin form widgets
- State transition validation

**Example Unit Tests:**
- Test that Case.validate() raises ValidationError for empty alleged_entities
- Test that Case.create_draft() creates a new draft record with state=DRAFT and incremented version
- Test that Case.publish() sets state=PUBLISHED
- Test that DocumentSource.save() generates source_id correctly
- Test that CasePermission.has_object_permission() returns correct values for different roles
- Test specific edge cases like editing a case with no contributors assigned
- Test that case_type and state use enum values correctly
- Test that tags field stores and retrieves list of strings correctly
- Test that DELETE operation sets state=CLOSED instead of hard deleting

### Property-Based Testing

The platform will use **Hypothesis** for property-based testing in Python.

**Configuration:**
- Minimum 100 iterations per property test
- Each property test will be tagged with: `# Feature: accountability-platform-core, Property {number}: {property_text}`

**Test Generators:**
- `case_data()`: Generates valid case dictionaries with random but valid entity IDs, key allegations, timeline, evidence
- `user_with_role(role)`: Generates User instances with specified role (Admin, Moderator, Contributor)
- `entity_id()`: Generates valid entity ID strings matching NES format
- `invalid_entity_id()`: Generates invalid entity ID strings for negative testing
- `state_transition(from_state, to_state)`: Generates state transition test cases

**Property Test Examples:**

```python
# Feature: accountability-platform-core, Property 1: New cases start in Draft state
@given(case_data=case_data(), contributor=user_with_role('Contributor'))
def test_new_cases_start_in_draft(case_data, contributor):
    case = Case.objects.create(**case_data)
    assert case.state == CaseState.DRAFT
    assert case.version == 1  # New cases start at version 1

# Feature: accountability-platform-core, Property 8: Role-based access control
@given(
    case=case_instance(),
    moderator=user_with_role('Moderator'),
    contributor=user_with_role('Contributor')
)
def test_role_based_access(case, moderator, contributor):
    # Moderator should always have access
    assert has_permission(moderator, case) == True
    # Contributor should only have access if assigned
    if contributor in case.contributors.all():
        assert has_permission(contributor, case) == True
    else:
        assert has_permission(contributor, case) == False
```

### End-to-End Testing

**Public API E2E Tests:**
- Test complete public user workflows: browse cases → filter → search → view details
- Test API filtering and search with various parameters
- Test that only published cases are accessible
- Test audit history retrieval for published cases

**Django Admin E2E Tests:**
- Test complete case management workflows: create draft → edit → submit → review → publish
- Test contributor assignment and access restrictions
- Test state transitions with validation
- Test version creation when editing published cases
- Test soft deletion (setting state to CLOSED)

### Test Data Management

**Fixtures:**
- `users.json`: Sample users with different roles
- `entities.json`: Sample entity IDs for testing
- `cases.json`: Sample cases in various states

**Factory Pattern:**
- Use factory functions to generate test data programmatically
- Ensure test isolation by cleaning up data after each test

## Performance Considerations

### Database Optimization

**Indexing Strategy:**
- **Primary index** on `Case.id` (Django auto-generated primary key)
- **Index** on `Case.case_id` for grouping versions of the same case
- **Index** on `Case.state` for filtering published cases
- **Index** on `Case.version` for ordering versions
- **Composite index** on `(case_id, state, version)` for finding current published version
- **Composite index** on `(state, version)` for common query patterns

**Query Optimization:**
- Use `select_related()` for foreign key relationships (User, Allegation)
- Use `prefetch_related()` for many-to-many relationships (contributors)
- Implement pagination for all list views (already configured: PAGE_SIZE=20)

### Caching Strategy

**Cache Candidates:**
- Published cases list (cache key: `cases:published:{page}`)
- Individual published cases (cache key: `case:{id}:published`)
- OpenAPI schema (cache key: `api:schema`)
- Cache invalidation on state change to Published

**Cache Implementation:**
- Use Django's cache framework with Redis backend (to be configured)
- Set appropriate TTL values (e.g., 5 minutes for lists, 15 minutes for detail views)

### API Rate Limiting

**Rate Limit Strategy:**
- Unauthenticated requests: 100 requests/hour per IP
- Authenticated requests: 1000 requests/hour per user
- Use Django REST Framework throttling classes

## Security Considerations

### Authentication & Authorization

**Authentication:**
- Django session-based authentication for admin interface
- Token-based authentication for API (to be implemented)
- CSRF protection enabled for state-changing operations

**Authorization:**
- Object-level permissions using django-rules
- Role-based access control enforced at API and model level
- Explicit permission checks before state transitions

### Input Validation

**Entity ID Validation:**
- Validate against NES format using `validate_entity_id()`
- Prevent injection attacks through strict format validation

**JSON Field Validation:**
- Validate structure of timeline, evidence, key_allegations
- Sanitize rich text input (TinyMCE configuration)
- Limit JSON field sizes to prevent DoS

### Data Protection

**Sensitive Data:**
- User passwords hashed using Django's default PBKDF2 algorithm
- No PII stored in allegation content (entity IDs only)
- Audit trail preserves user actions for accountability

**CORS Configuration:**
- Currently allows all origins (development)
- Production: Restrict to specific domains
- Only allow GET, HEAD, OPTIONS for public API

## Deployment Considerations

### Environment Configuration

**Required Environment Variables:**
- `SECRET_KEY`: Django secret key (must be unique in production)
- `DEBUG`: Set to False in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames
- `DATABASE_URL`: PostgreSQL connection string
- `NES_API_URL`: Nepal Entity Service API endpoint
- `CSRF_TRUSTED_ORIGINS`: Comma-separated list of trusted origins

### Database Migrations

**Migration Strategy:**
- Run migrations before deployment: `python manage.py migrate`
- Create initial user groups: `python manage.py create_groups`
- Backup database before running migrations in production

### Static Files

**Static File Handling:**
- Collect static files: `python manage.py collectstatic`
- Serve via CDN or web server (nginx) in production
- Configure `STATIC_ROOT` for production deployment

### Monitoring & Logging

**Logging Configuration:**
- Log all permission denials for security monitoring
- Log state transitions for audit purposes
- Log API errors for debugging
- Use structured logging (JSON format) for production

**Monitoring Metrics:**
- API response times
- Database query performance
- Cache hit rates
- Error rates by endpoint
- User activity by role

## Future Enhancements

### Potential Improvements

1. **Notification System**: Email/SMS notifications for state changes
2. **Bulk Operations**: Bulk assignment of contributors, bulk state changes
3. **Advanced Search**: Elasticsearch integration for better full-text search
4. **Export Functionality**: Export allegations to PDF, CSV formats
5. **Commenting System**: Allow internal comments on allegations during review
6. **Workflow Automation**: Automatic state transitions based on rules
7. **Analytics Dashboard**: Visualizations of allegation trends, entity statistics
8. **Mobile App**: Native mobile applications for iOS/Android
9. **Multi-language Support**: Nepali language interface and content
10. **Document Upload**: Direct file upload for evidence documents

### Scalability Considerations

**Horizontal Scaling:**
- Stateless API design allows multiple application servers
- Database connection pooling for efficient resource usage
- Separate read replicas for public API queries

**Vertical Scaling:**
- Optimize database queries as data grows
- Implement archival strategy for old cases
- Consider partitioning large tables by date
