from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Avg
from accounts.models import UserProfile
from core.models import DailyGoal, PenaltyReward
from functools import wraps

def admin_only(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.profile.role == 'admin' or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access Denied: You do not have permission to view the Company Panel.")
        return redirect('dashboard')
    return _wrapped_view

@admin_only
def admin_dashboard_view(request):
    """Global system overview for admins."""
    total_users = User.objects.count()
    total_goals = DailyGoal.objects.count()
    
    # Calculate success rate
    completed_goals = DailyGoal.objects.filter(status='completed').count()
    success_rate = round((completed_goals / total_goals * 100), 1) if total_goals > 0 else 0
    
    # Financials
    total_rewards = PenaltyReward.objects.filter(type='reward').aggregate(Sum('amount'))['amount__sum'] or 0
    total_penalties = PenaltyReward.objects.filter(type='penalty').aggregate(Sum('amount'))['amount__sum'] or 0
    
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    context = {
        'total_users': total_users,
        'total_goals': total_goals,
        'success_rate': success_rate,
        'total_rewards': total_rewards,
        'total_penalties': total_penalties,
        'recent_users': recent_users,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)

@admin_only
def user_list_view(request):
    """List of all users with performance metrics."""
    users = User.objects.all().select_related('profile').annotate(
        goal_count=Count('dailygoal'),
    )
    
    query = request.GET.get('q')
    if query:
        users = users.filter(username__icontains=query) | users.filter(email__icontains=query)
        
    return render(request, 'admin_dashboard/user_list.html', {'users': users, 'query': query})

@admin_only
def user_detail_view(request, user_id):
    """Detailed performance view for a single user."""
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    goals = DailyGoal.objects.filter(user=user).order_by('-date')
    transactions = PenaltyReward.objects.filter(user=user).order_by('-created_at')
    
    context = {
        'managed_user': user,
        'profile': profile,
        'goals': goals,
        'transactions': transactions,
    }
    return render(request, 'admin_dashboard/user_detail.html', context)
