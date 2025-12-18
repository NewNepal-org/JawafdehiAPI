# Cases App Instructions

## Context
Core Django app managing corruption allegations with revision system.

## Key Models
- **Case** - Main allegation with status workflow
- **Evidence** - Supporting documentation
- **Source** - Reference materials
- **Response** - Entity responses

## Patterns
- Use revision system for all case changes
- Implement permission checks with django-rules
- Follow DRF serializer patterns
- Maintain audit trails

## Status Workflow
Draft → In Review → Published/Closed

## Permission Rules
- Admin: Full access
- Moderator: All cases, can approve
- Contributor: Assigned cases only

Use authentic Nepali names in examples.