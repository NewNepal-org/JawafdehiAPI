# Implementation Plan

**Development Approach:** Follow Test-Driven Development (TDD). Write tests first, then implement the functionality to make the tests pass. This ensures all code is testable and meets requirements from the start.

- [x] 1. Write property tests for custom list field validation (TDD)
  - Write test for EntityListField validation
  - Write test for TextListField validation
  - Write test for TimelineListField validation
  - Write test for EvidenceListField validation
  - **Property 2: Draft validation is lenient, In Review validation is strict**
  - **Validates: Requirements 1.2**
  - _Requirements: 1.2, 4.1, 4.2_

- [x] 2. Implement custom list field types (to pass tests)
  - Create EntityListField for entity ID validation and storage
  - Create TextListField for text string lists
  - Create TimelineListField for timeline entries
  - Create EvidenceListField for evidence entries
  - _Requirements: 1.2, 4.1, 4.2_

- [x] 3. Write property tests for Case model (TDD)
  - Write test for new cases starting in Draft state
  - Write test for draft validation (lenient) vs In Review validation (strict)
  - Write test for draft submission transitions
  - Write test for draft creation incrementing version
  - Write test for editing published cases preserving original
  - **Property 1: New cases start in Draft state**
  - **Property 2: Draft validation is lenient, In Review validation is strict**
  - **Property 3: Draft submission transitions to In Review**
  - **Property 3a: Draft creation increments version**
  - **Property 4: Editing published cases preserves original**
  - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 7.1_

- [x] 4. Implement Case model with versioning (to pass tests)
  - Create Case model with all fields (case_id, version, case_type enum, state enum, etc.)
  - Implement validate() method for field validation
  - Implement create_draft() method for creating draft versions
  - Implement publish() method for publishing drafts
  - Add versionInfo JSONField tracking
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 7.1_

- [x] 5. Write property test for DocumentSource validation (TDD)
  - Write test for source validation enforcing required fields
  - **Property 11: Source validation enforces required fields**
  - **Validates: Requirements 4.2**
  - _Requirements: 4.1, 4.2_

- [x] 6. Implement DocumentSource model (to pass tests)
  - Create DocumentSource model with fields (source_id, title, description, url, etc.)
  - Add contributors ManyToMany field for access control
  - Implement validate() method
  - Add is_deleted field for soft deletion
  - _Requirements: 4.1, 4.2_

- [x] 7. Write property tests for Django Admin Case management (TDD)
  - Write test for moderator state transitions
  - Write test for versionInfo updates on state changes
  - **Property 6: Moderators can publish and close cases**
  - **Property 9: State transitions to IN_REVIEW, PUBLISHED, or CLOSED update versionInfo**
  - **Validates: Requirements 2.1, 2.4, 7.2**
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 8. Set up Django Admin for Case management (to pass tests)
  - Create custom admin form for Case with rich text editor
  - Implement inline editors for evidence and timeline
  - Add state transition controls with validation
  - Display version history and audit trail
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 9. Set up Django Admin for DocumentSource management
  - Create custom admin form for DocumentSource
  - Implement contributor-based access control
  - Auto-assign creator as contributor
  - Implement soft deletion interface
  - _Requirements: 4.1, 4.2_

- [x] 10. Write property tests for role-based permissions (TDD)
  - Write test for contributor state transitions (Draft ↔ In Review only)
  - Write test for admin permissions (full access)
  - Write test for contributor access restrictions (assigned cases only)
  - Write test for moderator restrictions (cannot manage other moderators)
  - **Property 5: Contributors can only transition between Draft and In Review**
  - **Property 12: Admin role-based permissions in Django Admin**
  - **Property 13: Contributor assignment restricts access in Django Admin**
  - **Property 14: Moderators cannot manage other Moderators in Django Admin**
  - **Validates: Requirements 1.5, 3.1, 3.2, 3.3, 5.1, 5.2, 5.3**
  - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 5.3_

- [x] 11. Implement role-based permissions in Django Admin (to pass tests)
  - Configure Admin, Moderator, and Contributor roles
  - Implement contributor assignment functionality
  - Restrict Contributor access to assigned cases only
  - Prevent Moderators from managing other Moderators
  - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 5.3_

- [x] 12. Write property tests for public API (TDD)
  - Write test for public API visibility (only published cases)
  - Write test for search and filter functionality
  - Write test for complete data display
  - Write test for evidence source references
  - **Property 8: Public API only shows published cases**
  - **Property 10: Evidence requires valid source references**
  - **Property 15: Search and filter functionality**
  - **Property 16: Published cases display complete data**
  - **Validates: Requirements 4.1, 6.1, 6.2, 6.3, 8.1, 8.3**
  - _Requirements: 4.1, 6.1, 6.2, 6.3, 8.1, 8.3_

- [x] 13. Implement public read-only API for Cases (to pass tests)
  - Create CaseViewSet with list and retrieve endpoints
  - Filter to show only published cases (highest version per case_id)
  - Implement filtering by case_type and tags
  - Implement full-text search across title, description, key_allegations
  - Include audit history (versionInfo) in retrieve endpoint
  - _Requirements: 6.1, 6.2, 6.3, 8.1, 8.3_

- [x] 14. Implement public read-only API for DocumentSources (to pass tests)
  - Create DocumentSourceViewSet with list and retrieve endpoints
  - Filter to show only sources referenced in evidence of published cases
  - _Requirements: 6.3_

- [x] 15. Set up OpenAPI documentation
  - Configure drf-spectacular for API documentation
  - Document all endpoints, filters, and response formats
  - _Requirements: 8.2_

- [x] 16. Write property test for soft deletion (TDD)
  - Write test for soft delete setting state to CLOSED
  - **Property 18: Soft delete sets state to CLOSED**
  - **Validates: Requirements 7.3**
  - _Requirements: 7.3_

- [x] 17. Implement soft deletion for Cases (to pass tests)
  - Add DELETE endpoint behavior to set state=CLOSED
  - Ensure closed cases remain in database
  - _Requirements: 7.3_

- [x] 18. Add database indexes
  - Add index on Case.case_id
  - Add index on Case.state
  - Add index on Case.version
  - Add composite index on (case_id, state, version)
  - Add composite index on (state, version)
  - _Performance optimization_

- [x] 19. Checkpoint - Ensure all property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 20. Write E2E tests for public API (TDD)
  - Test browse → filter → search → view details workflow
  - Test that only published cases are accessible
  - Test audit history retrieval
  - _Requirements: 6.1, 6.2, 6.3, 8.1, 8.3_

- [x] 21. Write E2E tests for Django Admin (TDD)
  - Test create draft → edit → submit → review → publish workflow
  - Test contributor assignment and access restrictions
  - Test state transitions with validation
  - Test version creation when editing published cases
  - Test soft deletion
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 5.1, 5.2, 5.3, 7.1, 7.3_

- [x] 22. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
