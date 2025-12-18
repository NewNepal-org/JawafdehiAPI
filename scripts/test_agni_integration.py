#!/usr/bin/env python3
"""
Test script for Agni integration.

This script tests the complete Agni workflow:
1. Upload a document
2. Monitor processing status
3. Resolve entities
4. Persist changes
"""

import os
import sys
import time
import requests
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class AgniIntegrationTester:
    """Test the Agni integration end-to-end."""
    
    def __init__(self, base_url='http://localhost:8080', username='admin', password='admin123'):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token = None
        
    def authenticate(self):
        """Authenticate and get API token."""
        print("🔐 Authenticating...")
        
        # Try to get existing token
        try:
            user = User.objects.get(username=self.username)
            token, created = Token.objects.get_or_create(user=user)
            self.token = token.key
            self.session.headers.update({'Authorization': f'Token {self.token}'})
            print(f"✅ Authenticated as {self.username}")
            return True
        except User.DoesNotExist:
            print(f"❌ User {self.username} not found")
            return False
    
    def create_test_document(self):
        """Create a test document for processing."""
        content = """
        भ्रष्टाचार मुद्दा रिपोर्ट
        
        यो रिपोर्टमा राम बहादुर गुरुङ र नेपाल सरकारको बारेमा जानकारी छ।
        
        मुख्य व्यक्तिहरू:
        - राम बहादुर गुरुङ (पूर्व मन्त्री)
        - सीता देवी शर्मा (सचिव)
        - हरि प्रसाद अधिकारी (निर्देशक)
        
        संस्थाहरू:
        - नेपाल सरकार
        - भ्रष्टाचार अनुसन्धान आयोग
        - सर्वोच्च अदालत
        
        स्थानहरू:
        - काठमाडौं
        - पोखरा
        - चितवन
        
        यो मुद्दा २०२४ सालमा दर्ता भएको थियो।
        """
        
        return ('test_corruption_case.txt', content.encode('utf-8'), 'text/plain')
    
    def upload_document(self):
        """Upload a document and create a session."""
        print("📄 Uploading test document...")
        
        files = {'document': self.create_test_document()}
        data = {'guidance': 'Extract all persons, organizations, and locations mentioned in this corruption case'}
        
        response = self.session.post(
            f'{self.base_url}/api/agni/sessions/',
            files=files,
            data=data
        )
        
        if response.status_code == 201:
            session_data = response.json()
            session_id = session_data['id']
            print(f"✅ Document uploaded successfully. Session ID: {session_id}")
            return session_id
        else:
            print(f"❌ Failed to upload document: {response.status_code}")
            print(response.text)
            return None
    
    def monitor_processing(self, session_id, max_wait=300):
        """Monitor session processing status."""
        print(f"⏳ Monitoring processing for session {session_id}...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = self.session.get(f'{self.base_url}/api/agni/sessions/{session_id}/')
            
            if response.status_code != 200:
                print(f"❌ Failed to get session status: {response.status_code}")
                return None
            
            data = response.json()
            status = data['status']
            tasks = data.get('tasks') or data.get('active_tasks', [])
            
            print(f"📊 Status: {status}, Tasks: {len(tasks)}")
            
            if status == 'awaiting_review':
                print("✅ Processing completed, ready for review")
                return data
            elif status == 'failed':
                print(f"❌ Processing failed: {data.get('error_message', 'Unknown error')}")
                return None
            elif status == 'completed':
                print("✅ Session completed")
                return data
            
            time.sleep(5)
        
        print("⏰ Timeout waiting for processing to complete")
        return None
    
    def resolve_entities(self, session_id, session_data):
        """Resolve entities in the session."""
        entities = session_data.get('entities', [])
        if not entities:
            print("ℹ️ No entities found to resolve")
            return True
        
        print(f"🎯 Resolving {len(entities)} entities...")
        
        for i, entity in enumerate(entities):
            entity_type = entity['entity_type']
            names = entity.get('names', [])
            candidates = entity.get('candidates', [])
            
            print(f"Entity {i}: {entity_type} - {names}")
            print(f"  Candidates: {len(candidates)}")
            
            # For demo purposes, we'll:
            # - Match entities with high-confidence candidates
            # - Create new entities with no candidates
            # - Skip entities with low confidence
            
            if candidates and candidates[0]['confidence'] > 0.9:
                # Match to existing entity
                action_data = {
                    'action': 'match',
                    'nes_id': candidates[0]['nes_id']
                }
                print(f"  → Matching to {candidates[0]['nes_id']}")
            elif entity['confidence'] > 0.8:
                # Create new entity
                action_data = {
                    'action': 'create',
                    'confirmed': True
                }
                print(f"  → Creating new entity")
            else:
                # Skip low-confidence entity
                action_data = {
                    'action': 'skip',
                    'reason': 'Low confidence entity'
                }
                print(f"  → Skipping (low confidence)")
            
            response = self.session.post(
                f'{self.base_url}/api/agni/sessions/{session_id}/entities/{i}/',
                json=action_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Resolved as: {result['entity_status']}")
            else:
                print(f"  ❌ Failed to resolve entity: {response.status_code}")
                print(f"     {response.text}")
                return False
        
        return True
    
    def persist_changes(self, session_id):
        """Persist the resolved changes."""
        print("💾 Persisting changes...")
        
        data = {
            'description': 'Test integration: Extracted entities from corruption case document',
            'confirm': True
        }
        
        response = self.session.post(
            f'{self.base_url}/api/agni/sessions/{session_id}/persist/',
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Changes persisted: {result['message']}")
            print(f"   Change IDs: {result['change_ids']}")
            return True
        else:
            print(f"❌ Failed to persist changes: {response.status_code}")
            print(response.text)
            return False
    
    def run_test(self):
        """Run the complete integration test."""
        print("🚀 Starting Agni integration test...")
        print("=" * 50)
        
        # Step 1: Authenticate
        if not self.authenticate():
            return False
        
        # Step 2: Upload document
        session_id = self.upload_document()
        if not session_id:
            return False
        
        # Step 3: Monitor processing
        session_data = self.monitor_processing(session_id)
        if not session_data:
            return False
        
        # Step 4: Resolve entities
        if not self.resolve_entities(session_id, session_data):
            return False
        
        # Step 5: Persist changes
        if not self.persist_changes(session_id):
            return False
        
        print("=" * 50)
        print("🎉 Integration test completed successfully!")
        return True


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Agni integration')
    parser.add_argument('--url', default='http://localhost:8080', help='API base URL')
    parser.add_argument('--username', default='admin', help='Username for authentication')
    parser.add_argument('--password', default='admin123', help='Password for authentication')
    
    args = parser.parse_args()
    
    tester = AgniIntegrationTester(
        base_url=args.url,
        username=args.username,
        password=args.password
    )
    
    success = tester.run_test()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()