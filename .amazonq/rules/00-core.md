# Amazon Q Rules - JawafdehiAPI

## Security First
- Never suggest committing secrets or `.env` files
- Always validate user permissions before data operations
- Maintain case revision audit trails - never delete history
- Use Django's built-in security features (CSRF, authentication)

## Django Best Practices
- Use Poetry for dependency management: `poetry run <command>`
- Follow Django 5.2+ conventions and patterns
- Use Django migrations for all schema changes
- Implement proper error handling and validation

## Code Correctness
- Test with pytest + hypothesis: `poetry run pytest`
- Format with black (88 chars) and isort: `poetry run black . && poetry run isort .`
- Use type hints where beneficial
- Follow established Models → Serializers → Views → URLs pattern

## Nepali Context
- Use authentic Nepali names in examples and fixtures
- Support bilingual content (English/Nepali)
- Consider local governance structures in design

See `AGENTS.md` for complete workflow and architecture details.