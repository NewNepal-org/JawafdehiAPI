# Django Settings Configuration for Agni UI

This document explains the Django settings configured to support the Agni UI React development environment.

## Automatic Configuration in DEBUG Mode

When `DEBUG=True`, the Django settings automatically configure:

### CSRF Protection

```python
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:7999",
    "http://127.0.0.1:7999",
]
```

This allows the React dev server to make authenticated requests to Django without CSRF errors.

### CORS Configuration

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:7999",
    "http://127.0.0.1:7999",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
```

This enables cross-origin requests from the React dev server with proper headers.

### Allowed Hosts

```python
ALLOWED_HOSTS.extend(["localhost:7999", "127.0.0.1:7999"])
```

Ensures Django accepts requests from the React dev server.

## Development Workflow

### 1. Start Django Backend

```bash
cd services/JawafdehiAPI
poetry run python manage.py runserver
```

Django will automatically:
- Enable CSRF trusted origins for port 7999
- Configure CORS for the React dev server
- Allow requests from localhost:7999

### 2. Start React Frontend

```bash
cd services/JawafdehiAPI/agni-ui
npm run dev
```

The React app will:
- Run on http://localhost:7999
- Proxy API requests to http://localhost:8000
- Include CSRF tokens in requests
- Send credentials with requests

## Production Configuration

In production (`DEBUG=False`), the settings revert to:

```python
CORS_ALLOW_ALL_ORIGINS = True  # Public API
CORS_ALLOW_METHODS = ["GET", "HEAD", "OPTIONS"]  # Read-only
```

The built React app is served from Django static files, so no CORS is needed.

## Environment Variables

You can override these settings using environment variables:

```bash
# .env file
DEBUG=True
CSRF_TRUSTED_ORIGINS=http://localhost:7999,https://beta.jawafdehi.org
ALLOWED_HOSTS=localhost,127.0.0.1,beta.jawafdehi.org
```

## Security Notes

### Development (DEBUG=True)
- ✅ CSRF protection enabled with trusted origins
- ✅ CORS restricted to specific origins
- ✅ Credentials allowed for authenticated requests
- ✅ All HTTP methods allowed for API development

### Production (DEBUG=False)
- ✅ CSRF protection fully enabled
- ✅ CORS allows all origins (public API)
- ✅ Only read-only methods allowed (GET, HEAD, OPTIONS)
- ✅ No credentials sent cross-origin

## Troubleshooting

### CSRF Token Errors

**Problem**: 403 Forbidden with CSRF verification failed

**Solution**: 
1. Ensure Django is running with `DEBUG=True`
2. Check that React dev server is on port 7999
3. Verify CSRF token is included in requests
4. Check browser console for CORS errors

### CORS Errors

**Problem**: CORS policy blocking requests

**Solution**:
1. Verify Django settings include port 7999 in CORS_ALLOWED_ORIGINS
2. Check that `corsheaders` is in INSTALLED_APPS
3. Ensure CorsMiddleware is before CommonMiddleware
4. Restart Django server after settings changes

### Connection Refused

**Problem**: Cannot connect to Django backend

**Solution**:
1. Ensure Django is running on port 8000
2. Check Vite proxy configuration in `vite.config.js`
3. Verify no firewall blocking localhost connections

## Testing the Configuration

### 1. Check Django Settings

```bash
cd services/JawafdehiAPI
poetry run python manage.py shell
```

```python
from django.conf import settings
print("DEBUG:", settings.DEBUG)
print("CSRF_TRUSTED_ORIGINS:", settings.CSRF_TRUSTED_ORIGINS)
print("CORS_ALLOWED_ORIGINS:", settings.CORS_ALLOWED_ORIGINS)
print("ALLOWED_HOSTS:", settings.ALLOWED_HOSTS)
```

### 2. Test API Endpoint

```bash
# Test from React dev server origin
curl -H "Origin: http://localhost:7999" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-CSRFToken" \
     -X OPTIONS \
     http://localhost:8000/api/agni/sessions/
```

Should return CORS headers allowing the request.

### 3. Test File Upload

1. Start both Django and React servers
2. Open http://localhost:7999
3. Upload a test document
4. Check Django logs for successful request
5. Verify no CSRF or CORS errors in browser console

## Additional Configuration

### Custom Port

If you need to use a different port for the React dev server:

1. Update `vite.config.js`:
```javascript
server: {
  port: YOUR_PORT,
}
```

2. Update Django settings in `config/settings.py`:
```python
AGNI_UI_DEV_ORIGINS = [
    f"http://localhost:{YOUR_PORT}",
    f"http://127.0.0.1:{YOUR_PORT}",
]
```

### Multiple Environments

For staging or other environments, use environment variables:

```bash
# .env.staging
DEBUG=True
CSRF_TRUSTED_ORIGINS=http://localhost:7999,https://staging.jawafdehi.org
CORS_ALLOWED_ORIGINS=http://localhost:7999,https://staging.jawafdehi.org
```

## References

- [Django CSRF Protection](https://docs.djangoproject.com/en/5.2/ref/csrf/)
- [Django CORS Headers](https://github.com/adamchainz/django-cors-headers)
- [Vite Proxy Configuration](https://vitejs.dev/config/server-options.html#server-proxy)