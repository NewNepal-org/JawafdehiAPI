#!/bin/bash

# Build script for integrating Agni UI with Django
# This script builds the React app and copies it to Django static files

set -e

echo "🚀 Building Agni UI for Django integration..."

# Navigate to the agni-ui directory
cd "$(dirname "$0")/.."

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build the React application
echo "🔨 Building React application..."
npm run build

# Create Django static directory if it doesn't exist
DJANGO_STATIC_DIR="../agni/static/agni-ui"
mkdir -p "$DJANGO_STATIC_DIR"

# Copy built files to Django static directory
echo "📁 Copying built files to Django static directory..."
cp -r dist/* "$DJANGO_STATIC_DIR/"

# Update the HTML template to use the correct root element ID
TEMPLATE_DIR="../agni/templates/agni"
TEMPLATE_FILE="$TEMPLATE_DIR/upload_document_react.html"

if [ -f "$TEMPLATE_FILE" ]; then
    echo "🔧 Updating Django template..."
    # Update the root element ID in the template
    sed -i.bak 's/id="root"/id="agni-document-processing"/g' "$TEMPLATE_FILE"
    rm -f "$TEMPLATE_FILE.bak"
fi

echo "✅ Build complete! Files copied to $DJANGO_STATIC_DIR"
echo ""
echo "Next steps:"
echo "1. Run 'poetry run python manage.py collectstatic' from the JawafdehiAPI directory"
echo "2. Restart your Django development server"
echo "3. Visit the Django admin to test the integration"
echo ""
echo "For development:"
echo "- Django backend: http://localhost:8000"
echo "- React frontend: http://localhost:7999"