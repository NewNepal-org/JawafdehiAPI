# Requirements Document

## Introduction

The Jawafdehi platform is a public accountability system for tracking allegations of corruption and misconduct by public entities in Nepal. The system supports a multi-role workflow where Contributors create and edit allegations, Moderators and Admins review and publish content, and the public can browse published cases. The platform implements a revision-based system to track all changes to allegations while maintaining a clear separation between draft work and published content.

## Glossary

- **Platform**: The Jawafdehi public accountability web application
- **Case** (or **Allegation**): A documented case of alleged corruption, misconduct, breach of trust, broken promise, or media trial against a public entity. Note: The Django model is named `Allegation` but we refer to it as a "Case" in user-facing documentation.
- **Revision**: A snapshot of a case's content at a specific point in time, used to track changes
- **Published Version**: The current live case visible to the public
- **Draft Revision**: A new version of a case that is being edited but not yet published
- **Contributor**: A user role that can create cases and edit assigned cases
- **Moderator**: A user role that can manage contributors and review/publish all cases
- **Admin**: A user role with full system access including moderator management
- **Case Assignment**: The explicit association of a Contributor with a Case, granting access rights
- **Evidence**: Supporting documentation linked to a case
- **Source**: A document or reference that provides evidence for a case
- **Entity**: A public organization or individual that can be the subject of cases (validated via Nepal Entity Service)

## Requirements

### Requirement 1

**User Story:** As a Contributor, I want to manage cases through a draft-review-publish workflow, so that I can document cases that are reviewed before publication.

#### Acceptance Criteria

1. WHEN a Contributor creates a case THEN the Platform SHALL set the initial state to Draft
2. WHEN creating a case THEN the Platform SHALL require at least one alleged entity with valid entity ID and at least one key allegation statement
3. WHEN a Contributor submits a draft THEN the Platform SHALL change the state to In Review
4. WHEN a Contributor edits a published case THEN the Platform SHALL create a new draft revision while preserving the published version
5. WHEN a Contributor is assigned to a case THEN the Platform SHALL allow state changes between Draft and In Review only

### Requirement 2

**User Story:** As a Moderator, I want to review and publish cases, so that only verified content becomes public.

#### Acceptance Criteria

1. WHEN a Moderator reviews a case with state In Review THEN the Platform SHALL allow changing the state to Published or Closed
2. WHEN a Moderator approves a revision as Published THEN the Platform SHALL make that revision the live public version
3. WHEN a Moderator accesses cases THEN the Platform SHALL provide access to all cases regardless of assignment or state
4. WHEN a Moderator changes case state THEN the Platform SHALL record the action in the modification history

### Requirement 3

**User Story:** As an Admin or Moderator, I want to assign Contributors to cases, so that they can access only their assigned work.

#### Acceptance Criteria

1. WHEN an Admin or Moderator assigns a Contributor to a case THEN the Platform SHALL grant access to the case and associated Evidence and Sources
2. WHEN a Contributor is not assigned to a case THEN the Platform SHALL deny all access to that case and its related content
3. WHEN checking case access THEN the Platform SHALL allow Admins and Moderators to access all cases regardless of assignment

### Requirement 4

**User Story:** As a Contributor, I want to add evidence and sources to my assigned cases, so that I can build comprehensive documentation.

#### Acceptance Criteria

1. WHEN a Contributor adds evidence to an assigned case THEN the Platform SHALL store the evidence with source ID and description
2. WHEN a Contributor adds a source document THEN the Platform SHALL validate required fields including title, description, and source type
3. WHEN a Contributor attempts to modify content for an unassigned case THEN the Platform SHALL reject the operation

### Requirement 5

**User Story:** As an Admin, I want to manage user roles, so that I can control access levels across the platform.

#### Acceptance Criteria

1. WHEN an Admin creates a Moderator account THEN the Platform SHALL grant access to all allegations and contributor management
2. WHEN an Admin creates a Contributor account THEN the Platform SHALL restrict access to assigned cases only
3. WHEN checking permissions THEN the Platform SHALL prevent Moderators from managing other Moderators

### Requirement 6

**User Story:** As a public user, I want to browse and view published cases, so that I can access accountability information.

#### Acceptance Criteria

1. WHEN an unauthenticated user accesses the case list THEN the Platform SHALL display only cases with state Published
2. WHEN a user filters or searches cases THEN the Platform SHALL support filtering by entity, category, status and searching across title, description, and key allegations
3. WHEN a user views a published case THEN the Platform SHALL display all associated evidence, sources, and timeline

### Requirement 7

**User Story:** As a system, I want to maintain a complete audit trail, so that the history of each case is preserved.

#### Acceptance Criteria

1. WHEN any case field is modified THEN the Platform SHALL create a new revision with a complete content snapshot
2. WHEN a user performs an action on a case THEN the Platform SHALL record the action type, timestamp, user, and notes in the modification history
3. WHEN querying revision history THEN the Platform SHALL return revisions in reverse chronological order

### Requirement 8

**User Story:** As a developer, I want to access case data via a RESTful API, so that I can build integrations and analysis tools.

#### Acceptance Criteria

1. WHEN an API client requests cases THEN the Platform SHALL return data in JSON format with support for filtering and full-text search
2. WHEN an API client accesses the API THEN the Platform SHALL provide OpenAPI documentation
3. WHEN an unauthenticated API client requests data THEN the Platform SHALL return only published cases
