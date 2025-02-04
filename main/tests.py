from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from .models import Vision, RICHItem, YearlyGoal, QuarterlyGoal, KPI, JournalEntry

class PGOSAPITests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = APIClient()
        
        # Get JWT token
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_vision_crud(self):
        # Create vision
        vision_data = {
            'title': 'Test Vision',
            'description': 'My test vision description'
        }
        response = self.client.post('/api/vision/', vision_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        vision_id = response.data['id']

        # Read vision
        response = self.client.get(f'/api/vision/{vision_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], vision_data['title'])

    def test_rich_item_crud(self):
        # Create RICH item
        rich_data = {
            'title': 'Test RICH',
            'description': 'Test description',
            'rich_type': 'responsibility'
        }
        response = self.client.post('/api/rich/', rich_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_dashboard_data(self):
        # Test dashboard endpoint
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('stats', response.data)
        self.assertIn('recent_activity', response.data)

    def test_unauthorized_access(self):
        # Remove credentials
        self.client.credentials()
        
        # Try to access protected endpoint
        response = self.client.get('/api/vision/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
