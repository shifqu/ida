"""Users app tests."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import Company
from apps.users.models import IdaUser


class UsersTestCase(TestCase):
    """Users test case."""

    fixtures = ["companies.json"]

    def test_create_user(self):
        """Test creating a user."""
        self.assertEqual(IdaUser, get_user_model())
        user = IdaUser.objects.create_user(username="testuser", email="testuser@example.com", password="testpass1234")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "testuser@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.language, "en")
        self.assertIsNone(user.company)

        user.company = Company.objects.get(pk=1)
        user.save()
        self.assertEqual(user.company, 1)

    def test_create_superuser(self):
        """Test creating a superuser."""
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username="testsuperuser", email="testsuperuser@example.com", password="testpass1234"
        )
        self.assertEqual(admin_user.username, "testsuperuser")
        self.assertEqual(admin_user.email, "testsuperuser@example.com")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
