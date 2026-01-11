from django.contrib.auth import get_user_model
from cases.models import DocumentSource

User = get_user_model()

# Create superuser
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
    print("Created admin user")
else:
    print("Admin user already exists")

# Create a test DocumentSource
if not DocumentSource.objects.filter(title='Test Source').exists():
    source = DocumentSource.objects.create(
        title='Test Source',
        description='This is a test source with multiple URLs',
        urls=['https://example.com', 'https://example.org'],
        publisher='Test Publisher',
        publication_date='2024-01-15'
    )
    print(f"Created test source: {source.source_id}")
else:
    print("Test source already exists")
