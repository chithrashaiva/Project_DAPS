from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    description = models.TextField()
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class Partnership(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='partnerships_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='partnerships_as_user2')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user1', 'user2')

    def __str__(self):
        return f"{self.user1.username} & {self.user2.username}"

class DailyUpdate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_updates')
    date = models.DateField(auto_now_add=True)
    achievements = models.TextField(help_text="What did you achieve today?")
    bottlenecks = models.TextField(help_text="What stopped you?")
    plan_for_tomorrow = models.TextField()
    mood_rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], default=3)

    def __str__(self):
        return f"{self.user.username} - {self.date}"
