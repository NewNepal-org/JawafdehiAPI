# Agni UI Quick Start

## Development Setup

### 1. Prerequisites
- Node.js 18+ or Bun
- Django JawafdehiAPI running on port 8000

### 2. Quick Start
```bash
cd services/JawafdehiAPI/agni-ui
npm run dev:start
```

This will:
- Install dependencies if needed
- Create `.env` from `.env.example` if needed  
- Start development server on port 7999

### 3. Manual Setup
```bash
# Install dependencies
npm install

# Copy environment config
cp .env.example .env

# Start development server
npm run dev
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run dev:start` - Quick start with setup
- `npm run build` - Build for production
- `npm run build:django` - Build and copy to Django static files
- `npm run lint` - Run ESLint

## Ports

- **React Dev Server**: http://localhost:7999
- **Django Backend**: http://localhost:8000 (must be running)

## Integration with Django

### Development
1. Start Django: `cd services/JawafdehiAPI && poetry run python manage.py runserver`
2. Start React: `cd services/JawafdehiAPI/agni-ui && npm run dev`
3. Visit: http://localhost:7999

### Production Build
```bash
npm run build:django
cd .. && poetry run python manage.py collectstatic
```

## Key Features

- ✅ Auto file upload on selection
- ✅ Real-time status polling
- ✅ Debug panel for development
- ✅ Bootstrap responsive UI
- ✅ Nepali context support
- ✅ WCAG 2.1 AA accessibility

## Troubleshooting

**CORS Errors**: Ensure Django settings include:
```python
CORS_ALLOWED_ORIGINS = ['http://localhost:7999']
```

**API Errors**: Check Django backend is running on port 8000

**Build Errors**: Run `npm install` to ensure dependencies are installed