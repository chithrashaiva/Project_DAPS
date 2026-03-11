from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Avg
from accounts.models import UserProfile, SystemWallet
from core.models import DailyGoal, PenaltyReward
from django.contrib.auth import authenticate, login
from accounts.forms import LoginForm, RegisterForm
from functools import wraps

def admin_login_view(request):
    """Dedicated login view for administrators and company users."""
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.role == 'admin':
            return redirect('admin_panel')
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin'):
                login(request, user)
                messages.success(request, f'Welcome back to the Company Panel, {user.username}!')
                return redirect('admin_panel')
            else:
                messages.error(request, 'Access Denied: This portal is restricted to Company and Administrative personnel only.')
                return redirect('admin_login')
        else:
            messages.error(request, 'Invalid credentials.')
    else:
        form = LoginForm()
        
    return render(request, 'admin_dashboard/admin_login.html', {'form': form})

def admin_only(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
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
    
    # System Bank
    system_bank = SystemWallet.get_wallet()
    
    context = {
        'total_users': total_users,
        'total_goals': total_goals,
        'success_rate': success_rate,
        'total_rewards': total_rewards,
        'total_penalties': total_penalties,
        'recent_users': recent_users,
        'bank_balance': system_bank.balance,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)

@admin_only
def user_list_view(request):
    """List of all users with performance metrics."""
    users = User.objects.all().select_related('profile').annotate(
        goal_count=Count('goals'),
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
    transactions = PenaltyReward.objects.filter(user=user).order_by('-applied_at')
    
    context = {
        'managed_user': user,
        'profile': profile,
        'goals': goals,
        'transactions': transactions,
    }
    return render(request, 'admin_dashboard/user_detail.html', context)

@admin_only
def delete_user_view(request, user_id):
    """Allow admins to delete a user."""
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, "You cannot delete your own admin account from here.")
        elif user.is_superuser:
            messages.error(request, "Cannot delete superuser.")
        else:
            username = user.username
            user.delete()
            messages.success(request, f'User {username} deleted successfully.')
        return redirect('admin_user_list')
    return redirect('admin_user_detail', user_id=user.id)


@admin_only
def create_user_view(request):
    """Allow admins to create a new user account directly."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_active = True  # Admin created users are active immediately
            user.save()
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('admin_user_list')
    else:
        form = RegisterForm()
    return render(request, 'admin_dashboard/create_user.html', {'form': form})


@admin_only
def manage_funds_view(request):
    """Allow admins to manually adjust the system bank balance."""
    wallet = SystemWallet.get_wallet()
    if request.method == 'POST':
        action = request.POST.get('action')
        amount = Decimal(request.POST.get('amount', '0'))
        
        if action == 'add':
            wallet.balance += amount
            messages.success(request, f'Added ${amount} to the system bank.')
        elif action == 'subtract':
            wallet.balance -= amount
            messages.success(request, f'Subtracted ${amount} from the system bank.')
        
        wallet.save()
        return redirect('admin_panel')
        
    return render(request, 'admin_dashboard/manage_funds.html', {'wallet': wallet})
