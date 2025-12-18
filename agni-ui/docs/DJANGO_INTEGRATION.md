# Django Integration Guide

This guide explains how to integrate the Agni UI React application with the Django JawafdehiAPI backend. The React app is located within the JawafdehiAPI project structure for better integration.

## Project Structure

```
services/JawafdehiAPI/
├── agni-ui/                    # React application
│   ├── src/                    # React source code
│   ├── dist/                   # Built application (after npm run build)
│   ├── package.json            # Node.js dependencies
│   └── vite.config.js          # Vite configuration
├── agni/                       # Django app
│   ├── static/agni/           # Django static files
│   ├── templates/             # Django templates
│   └── views.py               # API views
└── manage.py                   # Django management
```

## Backend Requirements

### Django Settings

When `DEBUG=True`, disable CSRF verification for the Agni API endpoints:

```python
# settings.py

# CSRF exemption for development
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:7999',
        'http://127.0.0.1:7999',
    ]
    
    # Allow CORS for development
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:7999',
        'http://127.0.0.1:7999',
    ]
    ]
```

### API Views

Ensure your API views handle CSRF appropriately:

```python
# views.py
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings

class SessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for document processing sessions
    """
    
    @method_decorator(csrf_exempt if settings.DEBUG else lambda x: x)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
```

### URL Configuration

```python
# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from agni.views import SessionViewSet

router = DefaultRouter()
router.register(r'sessions', SessionViewSet, basename='session')

urlpatterns = [
    path('api/agni/', include(router.urls)),
]
```

## API Endpoints

### Upload Document

**Endpoint**: `POST /api/agni/sessions/`

**Request**:
```
Content-Type: multipart/form-data

document: <file>
guidance: <string> (optional)
```

**Response**:
```json
{
  "id": "uuid",
  "document_name": "example.pdf",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z",
  "guidance": "Focus on financial irregularities"
}
```

### Get Session Status

**Endpoint**: `GET /api/agni/sessions/{id}/`

**Response**:
```json
{
  "id": "uuid",
  "document_name": "example.pdf",
  "status": "completed",
  "entities_extracted": 15,
  "cases_identified": 3,
  "error_message": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:05:00Z"
}
```

### Status Values

- `pending`: Initial upload, queued for processing
- `processing`: Document analysis in progress
- `extracting`: Entity extraction in progress
- `completed`: Processing finished successfully
- `failed`: Processing encountered an error

## CORS Configuration

Install and configure django-cors-headers:

```bash
poetry add django-cors-headers
```

```python
# settings.py

INSTALLED_APPS = [
    ...
    'corsheaders',
    ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    ...
]

# Development CORS settings
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:7999',
        'http://127.0.0.1:7999',
    ]
    CORS_ALLOW_CREDENTIALS = True
```

## Development Workflow

### 1. Start Django Backend

```bash
cd services/JawafdehiAPI
poetry run python manage.py runserver
```

Backend will be available at `http://localhost:8000`

### 2. Start React Frontend

```bash
cd services/JawafdehiAPI/agni-ui
npm run dev
```

Frontend will be available at `http://localhost:7999`

### 3. Test Integration

1. Open `http://localhost:7999` in your browser
2. Upload a test document
3. Monitor the Django console for API requests
4. Check the React debug panel for status updates

## Production Deployment

### Option 1: Serve from Django

Build the React app and serve it from Django:

```bash
# Build the React app
cd services/JawafdehiAPI/agni-ui
npm run build

# Copy to Django static files
cp -r dist/* ../agni/static/agni-ui/

# Collect static files
cd ..
poetry run python manage.py collectstatic --noinput
```

Update Django template:

```html
<!-- templates/agni/upload_document.html -->
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <title>Agni AI Document Processing</title>
    <link rel="stylesheet" href="{% static 'agni-ui/assets/index.css' %}">
</head>
<body>
    <div id="agni-document-processing"></div>
    <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}">
    <script type="module" src="{% static 'agni-ui/assets/index.js' %}"></script>
</body>
</html>
```

### Option 2: Separate Deployment

Deploy React app separately (e.g., Cloud Run, Vercel):

1. Configure production API URL in `.env.production`
2. Build the app: `npm run build`
3. Deploy `dist/` directory to hosting service
4. Configure CORS on Django backend for production domain

## Environment Variables

### Development (.env)

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_DEBUG=true
```

### Production (.env.production)

```env
VITE_API_BASE_URL=https://api.jawafdehi.org
VITE_DEBUG=false
```

## Troubleshooting

### CSRF Token Errors

**Problem**: 403 Forbidden on API requests

**Solution**: 
- Ensure `DEBUG=True` in Django settings for development
- Check CSRF_TRUSTED_ORIGINS includes frontend URL
- Verify CORS configuration

### API Connection Errors

**Problem**: Network errors when uploading

**Solution**:
- Verify Django backend is running on port 8000
- Check Vite proxy configuration in `vite.config.js`
- Inspect browser console for CORS errors

### File Upload Fails

**Problem**: Upload returns 400 or 500 error

**Solution**:
- Check Django file upload settings (MAX_UPLOAD_SIZE)
- Verify media directory permissions
- Check Django logs for detailed error messages

### Polling Not Working

**Problem**: Status doesn't update after upload

**Solution**:
- Verify session ID is returned from upload
- Check Django API endpoint returns correct status
- Monitor network tab for polling requests

## Security Considerations

### Production Checklist

- [ ] Disable DEBUG mode in Django
- [ ] Enable CSRF protection
- [ ] Configure proper CORS origins
- [ ] Use HTTPS for all connections
- [ ] Set secure cookie flags
- [ ] Implement rate limiting
- [ ] Add authentication/authorization
- [ ] Sanitize file uploads
- [ ] Validate file types and sizes
- [ ] Log security events

### CSRF in Production

```python
# settings.py (production)

DEBUG = False

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True

CORS_ALLOWED_ORIGINS = [
    'https://beta.jawafdehi.org',
    'https://jawafdehi.org',
]
```

## Testing

### Backend API Tests

```python
# tests/test_api.py
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

class SessionAPITestCase(TestCase):
    def test_upload_document(self):
        file = SimpleUploadedFile(
            "test.txt",
            b"Test document content",
            content_type="text/plain"
        )
        
        response = self.client.post(
            '/api/agni/sessions/',
            {'document': file, 'guidance': 'Test guidance'},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.json())
```

### Frontend Integration Tests

Use the debug panel to verify:
- Upload progress tracking
- Status polling intervals
- Error handling and recovery
- Session state management