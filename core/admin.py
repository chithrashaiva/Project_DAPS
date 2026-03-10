from django.contrib import admin
from .models import PartnerRequest, DailyGoal, ProgressLog, PenaltyReward


@admin.register(PartnerRequest)
class PartnerRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('from_user__username', 'to_user__username')


@admin.register(DailyGoal)
class DailyGoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'phase', 'date', 'deadline', 'penalty_amount')
    list_filter = ('status', 'phase', 'date')
    search_fields = ('title', 'user__username')


@admin.register(ProgressLog)
class ProgressLogAdmin(admin.ModelAdmin):
    list_display = ('goal', 'note', 'timestamp')
    list_filter = ('timestamp',)


@admin.register(PenaltyReward)
class PenaltyRewardAdmin(admin.ModelAdmin):
    list_display = ('user', 'goal', 'type', 'amount', 'applied_at')
    list_filter = ('type', 'applied_at')
    search_fields = ('user__username',)
