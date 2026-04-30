from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from .models import Guard, Visitor

class DashboardAPITests(APITestCase):
    
    def setUp(self):
        # 1. ARRANGE: This runs before every single test. 
        # We create a fake user and guard in the temporary test database.
        self.user = User.objects.create_user(username='testguard', password='testpassword123')
        self.guard = Guard.objects.create(user=self.user, phone_number='1112223333', shift='Morning')
        
        # We use reverse() to look up the exact URL path using the 'name' from urls.py
        self.url = reverse('api_dashboard')

    def test_dashboard_blocks_unauthorized_users(self):
        # 2. ACT: Try to get the dashboard WITHOUT logging in
        response = self.client.get(self.url)

        # 3. ASSERT: We expect the server to kick us out with a 401 error
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_allows_authorized_guards(self):
        # 2. ACT: Force the test client to authenticate using our fake guard
        self.client.force_authenticate(user=self.user)
        
        # Now try to get the dashboard again
        response = self.client.get(self.url)

        # 3. ASSERT: We expect the server to allow us in with a 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class CheckInAPITests(APITestCase):
    
    def setUp(self):
        # Create our fake guard again for this specific test suite
        self.user = User.objects.create_user(username='postguard', password='testpassword123')
        self.guard = Guard.objects.create(user=self.user, phone_number='9998887777', shift='Evening')
        self.url = reverse('api_check_in')

    def test_successful_manual_check_in(self):
        # 1. Log the test robot in
        self.client.force_authenticate(user=self.user)
        
        # 2. ARRANGE: Create the fake JSON data a mobile app would send
        payload = {
            "name": "Automated Tester",
            "phone_number": "5551112222",
            "person_to_meet": "Mrs. Gupta",
            "purpose": "Meeting"
        }
        
        # 3. ACT: Send a POST request with the data
        response = self.client.post(self.url, payload, format='json')
        
        # 4. ASSERT: Did the API reply with a 201 Created status?
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 5. ASSERT (The Senior Move): Did it actually save to PostgreSQL?
        self.assertEqual(Visitor.objects.count(), 1)
        self.assertEqual(Visitor.objects.first().name, "Automated Tester")

    def test_check_in_fails_without_phone_number(self):
        self.client.force_authenticate(user=self.user)
        
        # 1. ARRANGE: Create bad data (missing the required phone number)
        bad_payload = {
            "name": "Hacker Man",
            "person_to_meet": "Mrs. Gupta",
            "purpose": "Meeting"
        }
        
        # 2. ACT: Send the bad POST request
        response = self.client.post(self.url, bad_payload, format='json')
        
        # 3. ASSERT: Did DRF block it and return a 400 Bad Request?
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # 4. ASSERT: Ensure the database remains completely empty
        self.assertEqual(Visitor.objects.count(), 0)