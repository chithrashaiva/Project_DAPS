from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.contrib.auth.models import User
from .models import Goal, DailyUpdate, Partnership, UserProfile
from .forms import GoalForm, DailyUpdateForm

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'accountability/register.html', {'form': form})

@login_required
def dashboard(request):
    goals = Goal.objects.filter(user=request.user)
    daily_updates = DailyUpdate.objects.filter(user=request.user).order_by('-date')
    
    # Simple logic to find partner
    partnerships = Partnership.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    partner = None
    if partnerships.exists():
        p = partnerships.first()
        partner = p.user2 if p.user1 == request.user else p.user1
        partner_updates = DailyUpdate.objects.filter(user=partner).order_by('-date')[:5]
    else:
        partner_updates = []

    if request.method == 'POST':
        goal_form = GoalForm(request.POST)
        if goal_form.is_valid():
            goal = goal_form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect('dashboard')
    else:
        goal_form = GoalForm()

    return render(request, 'accountability/dashboard.html', {
        'goals': goals,
        'daily_updates': daily_updates,
        'partner': partner,
        'partner_updates': partner_updates,
        'goal_form': goal_form,
    })

@login_required
def daily_update_view(request):
    if request.method == 'POST':
        form = DailyUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.user = request.user
            update.save()
            return redirect('dashboard')
    else:
        form = DailyUpdateForm()
    return render(request, 'accountability/daily_update.html', {'form': form})

@login_required
def find_partner(request):
    # Find users who are NOT the current user AND don't have an active partnership
    # This is a simplified version: just show all other users for now
    existing_partnerships = Partnership.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    if existing_partnerships.exists():
        return redirect('dashboard')
        
    users = User.objects.exclude(id=request.user.id).exclude(
        Q(partnerships_as_user1__is_active=True) | Q(partnerships_as_user2__is_active=True)
    )
    return render(request, 'accountability/find_partner.html', {'users': users})

@login_required
def connect_partner(request, user_id):
    partner = User.objects.get(id=user_id)
    # Check if a partnership already exists
    if not Partnership.objects.filter(
        Q(user1=request.user, user2=partner) | Q(user1=partner, user2=request.user)
    ).exists():
        Partnership.objects.create(user1=request.user, user2=partner)
    return redirect('dashboard')
