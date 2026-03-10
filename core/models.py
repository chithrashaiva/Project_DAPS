from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class PartnerRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ({self.status})"


class DailyGoal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    PHASE_CHOICES = [
        ('morning', 'Morning Commitment'),
        ('midday', 'Mid-Day Support'),
        ('evening', 'Evening Review'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    date = models.DateField(default=timezone.now)
    deadline = models.DateTimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    phase = models.CharField(max_length=10, choices=PHASE_CHOICES, default='morning')
    penalty_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('10.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def is_overdue(self):
        return timezone.now() > self.deadline and self.status not in ('completed', 'failed')


class ProgressLog(models.Model):
    goal = models.ForeignKey(DailyGoal, on_delete=models.CASCADE, related_name='progress_logs')
    note = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Progress on {self.goal.title} at {self.timestamp}"


class PenaltyReward(models.Model):
    TYPE_CHOICES = [
        ('penalty', 'Penalty'),
        ('reward', 'Reward'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    goal = models.ForeignKey(DailyGoal, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.type.title()}: ${self.amount} for {self.user.username}"
