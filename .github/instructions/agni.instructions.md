# Agni AI Integration Instructions

## Context
AI assistant integration for case analysis and content generation.

## Key Components
- Django app with models and views
- React UI in agni-ui/ subdirectory
- Integration with main cases system

## Development
- Backend: Django patterns with DRF
- Frontend: React + TypeScript + Vite
- API endpoints for AI interactions

## Security
- Validate all AI-generated content
- Maintain audit trails for AI actions
- Respect user permissions

## Commands
```bash
# Backend
poetry run python manage.py runserver

# Frontend (from agni-ui/)
npm run dev
```