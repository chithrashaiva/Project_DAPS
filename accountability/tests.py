from django.test import TestCase
from django.contrib.auth.models import User
from .models import UserProfile, Goal, Partnership, DailyUpdate

class AccountabilityModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='alice', password='password123')
        self.user2 = User.objects.create_user(username='bob', password='password123')

    def test_user_profile_creation(self):
        profile = UserProfile.objects.create(user=self.user1, bio="Test Bio")
        self.assertEqual(profile.user.username, 'alice')
        self.assertEqual(str(profile), 'alice')

    def test_goal_creation(self):
        goal = Goal.objects.create(user=self.user1, title="Test Goal", description="Test Description")
        self.assertEqual(goal.title, "Test Goal")
        self.assertFalse(goal.is_completed)

    def test_partnership_creation(self):
        partnership = Partnership.objects.create(user1=self.user1, user2=self.user2)
        self.assertTrue(partnership.is_active)
        self.assertEqual(str(partnership), "alice & bob")

    def test_daily_update_creation(self):
        update = DailyUpdate.objects.create(
            user=self.user1,
            achievements="Finished tests",
            bottlenecks="None",
            plan_for_tomorrow="Build views",
            mood_rating=5
        )
        self.assertEqual(update.mood_rating, 5)
        self.assertEqual(update.user.username, 'alice')
