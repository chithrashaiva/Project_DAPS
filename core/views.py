from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from decimal import Decimal

from .models import PartnerRequest, DailyGoal, ProgressLog, PenaltyReward
from .forms import GoalForm, ProgressLogForm, PartnerSearchForm


@login_required
def dashboard(request):
    """Main dashboard — the hub of the Low-Friction Protocol."""
    today = timezone.now().date()
    profile = request.user.profile

    # Today's goals grouped by phase
    todays_goals = DailyGoal.objects.filter(user=request.user, date=today)
    morning_goals = todays_goals.filter(phase='morning')
    midday_goals = todays_goals.filter(phase='midday')
    evening_goals = todays_goals.filter(phase='evening')

    # Stats
    total_goals = DailyGoal.objects.filter(user=request.user).count()
    completed_goals = DailyGoal.objects.filter(user=request.user, status='completed').count()
    failed_goals = DailyGoal.objects.filter(user=request.user, status='failed').count()
    completion_rate = round((completed_goals / total_goals * 100), 1) if total_goals > 0 else 0

    # Check overdue goals and apply consequences
    overdue_goals = DailyGoal.objects.filter(
        user=request.user,
        status__in=['pending', 'in_progress'],
        deadline__lt=timezone.now()
    )
    for goal in overdue_goals:
        _apply_penalty(request.user, goal)

    # Recent transactions
    recent_transactions = PenaltyReward.objects.filter(user=request.user)[:5]

    # Partner info
    partner = profile.partner
    partner_goals_today = None
    if partner:
        partner_goals_today = DailyGoal.objects.filter(user=partner, date=today)

    # Pending partner requests
    pending_requests = PartnerRequest.objects.filter(to_user=request.user, status='pending').count()

    context = {
        'today': today,
        'morning_goals': morning_goals,
        'midday_goals': midday_goals,
        'evening_goals': evening_goals,
        'total_goals': total_goals,
        'completed_goals': completed_goals,
        'failed_goals': failed_goals,
        'completion_rate': completion_rate,
        'wallet_balance': profile.wallet_balance,
        'recent_transactions': recent_transactions,
        'partner': partner,
        'partner_goals_today': partner_goals_today,
        'pending_requests': pending_requests,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def create_goal(request):
    """Morning Commitment — create a daily goal."""
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.date = timezone.now().date()
            goal.save()
            messages.success(request, f'Goal "{goal.title}" committed! Stay focused. 💪')
            return redirect('dashboard')
    else:
        form = GoalForm()

    return render(request, 'core/goal_form.html', {'form': form, 'action': 'Create'})


@login_required
def update_goal(request, goal_id):
    """Update goal status or add progress notes."""
    goal = get_object_or_404(DailyGoal, id=goal_id, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'complete':
            if goal.status != 'completed':
                goal.status = 'completed'
                goal.save()
                _apply_reward(request.user, goal)
                messages.success(request, f'🎉 Goal "{goal.title}" completed! Reward applied!')
            return redirect('dashboard')

        elif action == 'in_progress':
            goal.status = 'in_progress'
            goal.save()
            messages.info(request, f'Goal "{goal.title}" marked as in progress.')
            return redirect('dashboard')

        elif action == 'add_note':
            note_form = ProgressLogForm(request.POST)
            if note_form.is_valid():
                log = note_form.save(commit=False)
                log.goal = goal
                log.save()
                messages.success(request, 'Progress note added!')
            return redirect('goal_detail', goal_id=goal.id)

    note_form = ProgressLogForm()
    progress_logs = goal.progress_logs.all()
    transactions = goal.transactions.all()

    return render(request, 'core/goal_detail.html', {
        'goal': goal,
        'note_form': note_form,
        'progress_logs': progress_logs,
        'transactions': transactions,
    })


@login_required
def goal_list(request):
    """View all goals with filtering."""
    goals = DailyGoal.objects.filter(user=request.user)

    status_filter = request.GET.get('status')
    if status_filter:
        goals = goals.filter(status=status_filter)

    date_filter = request.GET.get('date')
    if date_filter:
        goals = goals.filter(date=date_filter)

    return render(request, 'core/goal_list.html', {
        'goals': goals,
        'current_status': status_filter,
        'current_date': date_filter,
    })


@login_required
def find_partners(request):
    """Search for accountability partners globally."""
    results = []
    form = PartnerSearchForm()

    if request.method == 'POST':
        form = PartnerSearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = User.objects.filter(
                Q(username__icontains=query) | Q(email__icontains=query)
            ).exclude(id=request.user.id)[:20]

    # Check existing requests
    sent_requests = PartnerRequest.objects.filter(
        from_user=request.user
    ).values_list('to_user_id', flat=True)

    return render(request, 'core/find_partners.html', {
        'form': form,
        'results': results,
        'sent_requests': list(sent_requests),
    })


@login_required
def send_partner_request(request, user_id):
    """Send a partner request to another user."""
    to_user = get_object_or_404(User, id=user_id)

    if to_user == request.user:
        messages.error(request, "You can't send a request to yourself.")
        return redirect('find_partners')

    existing = PartnerRequest.objects.filter(
        Q(from_user=request.user, to_user=to_user) |
        Q(from_user=to_user, to_user=request.user)
    ).filter(status__in=['pending', 'accepted']).exists()

    if existing:
        messages.warning(request, 'A request already exists between you two.')
    else:
        PartnerRequest.objects.create(from_user=request.user, to_user=to_user)
        messages.success(request, f'Partner request sent to {to_user.username}!')

    return redirect('find_partners')


@login_required
def partner_requests(request):
    """View and manage partner requests."""
    incoming = PartnerRequest.objects.filter(to_user=request.user, status='pending')
    outgoing = PartnerRequest.objects.filter(from_user=request.user, status='pending')

    return render(request, 'core/partner_requests.html', {
        'incoming': incoming,
        'outgoing': outgoing,
    })


@login_required
def handle_partner_request(request, request_id, action):
    """Accept or reject a partner request."""
    partner_req = get_object_or_404(PartnerRequest, id=request_id, to_user=request.user, status='pending')

    if action == 'accept':
        partner_req.status = 'accepted'
        partner_req.save()

        # Set both users as partners
        my_profile = request.user.profile
        their_profile = partner_req.from_user.profile

        # Remove old partnerships if any
        if my_profile.partner:
            old_partner_profile = my_profile.partner.profile
            old_partner_profile.partner = None
            old_partner_profile.save()
        if their_profile.partner:
            old_partner_profile2 = their_profile.partner.profile
            old_partner_profile2.partner = None
            old_partner_profile2.save()

        my_profile.partner = partner_req.from_user
        my_profile.save()
        their_profile.partner = request.user
        their_profile.save()

        messages.success(request, f'You are now partners with {partner_req.from_user.username}! 🤝')

    elif action == 'reject':
        partner_req.status = 'rejected'
        partner_req.save()
        messages.info(request, f'Request from {partner_req.from_user.username} rejected.')

    return redirect('partner_requests')


@login_required
def partner_progress(request):
    """View your partner's goals and progress."""
    profile = request.user.profile
    partner = profile.partner

    if not partner:
        messages.info(request, 'You don\'t have a partner yet. Find one!')
        return redirect('find_partners')

    today = timezone.now().date()
    partner_goals = DailyGoal.objects.filter(user=partner)
    partner_goals_today = partner_goals.filter(date=today)

    # Partner stats
    total = partner_goals.count()
    completed = partner_goals.filter(status='completed').count()
    completion_rate = round((completed / total * 100), 1) if total > 0 else 0

    return render(request, 'core/partner_progress.html', {
        'partner': partner,
        'partner_goals_today': partner_goals_today,
        'partner_goals_all': partner_goals[:30],
        'total_goals': total,
        'completed_goals': completed,
        'completion_rate': completion_rate,
    })


def _apply_penalty(user, goal):
    """Apply penalty for a failed goal."""
    if goal.transactions.filter(type='penalty').exists():
        return  # Already penalized

    goal.status = 'failed'
    goal.save()

    penalty_amount = goal.penalty_amount
    profile = user.profile
    profile.wallet_balance -= penalty_amount
    profile.save()

    PenaltyReward.objects.create(
        user=user,
        goal=goal,
        amount=penalty_amount,
        type='penalty',
    )


def _apply_reward(user, goal):
    """Apply reward (2x penalty) for a completed goal."""
    if goal.transactions.filter(type='reward').exists():
        return  # Already rewarded

    reward_amount = goal.penalty_amount * 2
    profile = user.profile
    profile.wallet_balance += reward_amount
    profile.save()

    PenaltyReward.objects.create(
        user=user,
        goal=goal,
        amount=reward_amount,
        type='reward',
    )
