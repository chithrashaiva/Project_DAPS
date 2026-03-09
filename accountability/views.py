from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import Goal, DailyUpdate, Partnership, UserProfile
from .forms import GoalForm, DailyUpdateForm, PartnerConnectionForm

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
    # Fetch partnership
    partnership = Partnership.objects.filter(Q(user1=request.user) | Q(user2=request.user)).first()
    
    partner = None
    partner_updates = []
    partner_missing_update = False
    
    if partnership:
        partner = partnership.user2 if partnership.user1 == request.user else partnership.user1
        partner_updates = DailyUpdate.objects.filter(user=partner).order_by('-date')[:5]
        
        # Check if partner has updated today
        from django.utils import timezone
        today = timezone.now().date()
        partner_has_updated = DailyUpdate.objects.filter(user=partner, date=today).exists()
        partner_missing_update = not partner_has_updated

    # Fetch individual goals AND shared goals
    if partnership:
        goals = Goal.objects.filter(Q(user=request.user) | Q(partnership=partnership)).distinct()
    else:
        goals = Goal.objects.filter(user=request.user)

    daily_updates = DailyUpdate.objects.filter(user=request.user).order_by('-date')
    
    # Calculate missed goals and penalties
    from django.utils import timezone
    now = timezone.now().date()
    missed_goals = goals.filter(deadline__lt=now, is_completed=False)
    total_penalty_count = missed_goals.count()

    if request.method == 'POST':
        goal_form = GoalForm(request.POST)
        if goal_form.is_valid():
            goal = goal_form.save(commit=False)
            goal.user = request.user
            # Check if it's a shared goal (from checkbox or hidden input)
            if (goal_form.cleaned_data.get('is_shared') or request.POST.get('is_shared')) and partnership:
                goal.partnership = partnership
            goal.save()
            return redirect('dashboard')
    else:
        goal_form = GoalForm()

    return render(request, 'accountability/dashboard.html', {
        'goals': goals,
        'missed_goals': missed_goals,
        'total_penalty_count': total_penalty_count,
        'daily_updates': daily_updates,
        'partner': partner,
        'partner_updates': partner_updates,
        'partner_missing_update': partner_missing_update,
        'goal_form': goal_form,
        'has_partnership': bool(partnership),
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
def add_partner(request):
    # If user already has a partner, redirect to dashboard
    if Partnership.objects.filter(Q(user1=request.user) | Q(user2=request.user)).exists():
        return redirect('dashboard')
        
    error_message = None
    if request.method == 'POST':
        form = PartnerConnectionForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Authenticate the potential partner
            partner = authenticate(request, username=username, password=password)
            
            if partner:
                if partner == request.user:
                    error_message = "You cannot be your own partner!"
                elif Partnership.objects.filter(Q(user1=partner) | Q(user2=partner)).exists():
                    error_message = "That user already has a partner."
                else:
                    # Create the partnership
                    Partnership.objects.create(user1=request.user, user2=partner)
                    return redirect('dashboard')
            else:
                error_message = "Invalid username or password for the partner."
    else:
        form = PartnerConnectionForm()
        
    return render(request, 'accountability/add_partner.html', {
        'form': form,
        'error_message': error_message
    })

@login_required
def connect_partner(request, user_id):
    partner = User.objects.get(id=user_id)
    # Check if a partnership already exists
    if not Partnership.objects.filter(
        Q(user1=request.user, user2=partner) | Q(user1=partner, user2=request.user)
    ).exists():
        Partnership.objects.create(user1=request.user, user2=partner)
    return redirect('dashboard')

@login_required
def complete_goal(request, goal_id):
    goal = Goal.objects.get(id=goal_id)
    # Check if user owns the goal or it's a shared goal for their partnership
    partnership = Partnership.objects.filter(Q(user1=request.user) | Q(user2=request.user)).first()
    if goal.user == request.user or (goal.partnership and goal.partnership == partnership):
        goal.is_completed = not goal.is_completed
        goal.save()
    return redirect('dashboard')
