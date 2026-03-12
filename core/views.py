from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from decimal import Decimal
from accounts.models import UserProfile, SystemWallet

from .models import PartnerRequest, DailyGoal, ProgressLog, PenaltyReward, GoalCollaborationRequest, GoalMessage
from .forms import GoalForm, ProgressLogForm, PartnerSearchForm
from functools import wraps

def user_only(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'profile') and request.user.profile.role == 'admin':
            messages.error(request, 'Company personnel cannot participate in goals or partnerships.')
            return redirect('admin_panel')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@user_only
def dashboard(request):
    """Main dashboard — the hub of the Low-Friction Protocol."""
    today = timezone.now().date()
    profile = request.user.profile

    # Active goals (including shared and past but not finished)
    todays_goals = DailyGoal.objects.filter(user=request.user, date=today)
    active_goals = DailyGoal.objects.filter(
        Q(user=request.user) | Q(collaborators=request.user),
        status__in=['pending', 'in_progress']
    )
    
    # Combined list for dashboard phases (Today's goals + Past Active)
    all_visible_goals = (todays_goals | active_goals).distinct()
    
    morning_goals = all_visible_goals.filter(phase='morning')
    midday_goals = all_visible_goals.filter(phase='midday')
    evening_goals = all_visible_goals.filter(phase='evening')

    # Stats
    total_goals = DailyGoal.objects.filter(user=request.user).count()
    completed_goals = DailyGoal.objects.filter(user=request.user, status='completed').count()
    failed_goals = DailyGoal.objects.filter(user=request.user, status='failed').count()
    completion_rate = round((completed_goals / total_goals * 100), 1) if total_goals > 0 else 0

    # Check overdue goals and apply consequences (for all active goals the user owns or collaborates on)
    overdue_goals = active_goals.filter(deadline__lt=timezone.now())
    for goal in overdue_goals:
        _apply_penalty(goal.user, goal) # _apply_penalty handles distribution
    
    if overdue_goals.exists():
        profile.refresh_from_db()

    # Recent transactions
    recent_transactions = PenaltyReward.objects.filter(user=request.user)[:5]

    # Partner info
    partner = profile.partner
    partner_goals_today = None
    if partner:
        partner_goals_today = DailyGoal.objects.filter(user=partner, date=today)

    # Pending partner requests
    pending_requests = PartnerRequest.objects.filter(to_user=request.user, status='pending').count()

    # Shared/Collaborative goals (for special section if needed, though they are now in phases too)
    shared_goals = active_goals.filter(is_shared=True)

    context = {
        'today': today,
        'morning_goals': morning_goals,
        'midday_goals': midday_goals,
        'evening_goals': evening_goals,
        'shared_goals': shared_goals,
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
@user_only
def create_goal(request):
    """Morning Commitment — create a daily goal."""
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.date = timezone.now().date()
            goal.save()
            
            # If shared and has partner, send invitation
            if goal.is_shared:
                profile = request.user.profile
                if profile.partner:
                    GoalCollaborationRequest.objects.create(
                        goal=goal,
                        sender=request.user,
                        receiver=profile.partner
                    )
                    messages.success(request, f'Goal "{goal.title}" created and invitation sent to {profile.partner.username}! 🤝')
                else:
                    messages.warning(request, f'Goal "{goal.title}" created as shared, but you don\'t have a partner to invite yet.')
            else:
                messages.success(request, f'Goal "{goal.title}" committed! Stay focused. 💪')
            
            return redirect('dashboard')
    else:
        form = GoalForm()

    return render(request, 'core/goal_form.html', {'form': form, 'action': 'Create'})


@login_required
@user_only
def propose_goal(request):
    """Suggest a shared goal to a partner."""
    profile = request.user.profile
    partner = profile.partner
    
    if not partner:
        messages.error(request, 'You need a partner to suggest a goal.')
        return redirect('find_partners')

    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.date = timezone.now().date()
            goal.is_shared = True # Always shared for suggestions
            goal.save()
            
            # Send invitation
            GoalCollaborationRequest.objects.create(
                goal=goal,
                sender=request.user,
                receiver=partner
            )
            messages.success(request, f'Goal suggested! Invitation sent to {partner.username}. 💡')
            return redirect('partner_progress')
    else:
        # Pre-set is_shared for suggestions
        form = GoalForm(initial={'is_shared': True})

    return render(request, 'core/goal_form.html', {
        'form': form, 
        'action': 'Suggest',
        'is_suggestion': True
    })


@login_required
@user_only
def update_goal(request, goal_id):
    """Update goal status or add progress notes."""
    # Support for collaborative goals
    goal = get_object_or_404(DailyGoal, Q(user=request.user) | Q(collaborators=request.user), id=goal_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'complete':
            if goal.status != 'completed':
                goal.status = 'completed'
                goal.save()
                _apply_reward(goal.user, goal)
                messages.success(request, f'🎉 Goal "{goal.title}" completed! Rewards distributed!')
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

        elif action == 'send_message':
            content = request.POST.get('content')
            if content:
                GoalMessage.objects.create(
                    goal=goal,
                    sender=request.user,
                    content=content
                )
            return redirect('goal_detail', goal_id=goal.id)

    note_form = ProgressLogForm()
    progress_logs = goal.progress_logs.all()
    transactions = goal.transactions.all()
    chat_messages = goal.messages.all()

    return render(request, 'core/goal_detail.html', {
        'goal': goal,
        'note_form': note_form,
        'progress_logs': progress_logs,
        'transactions': transactions,
        'chat_messages': chat_messages,
    })


@login_required
@user_only
def goal_invitations(request):
    """View and manage goal collaboration invitations."""
    incoming = GoalCollaborationRequest.objects.filter(receiver=request.user, status='pending')
    outgoing = GoalCollaborationRequest.objects.filter(sender=request.user, status='pending')

    return render(request, 'core/goal_invitations.html', {
        'incoming': incoming,
        'outgoing': outgoing,
    })


@login_required
@user_only
def handle_goal_invitation(request, invitation_id, action):
    """Accept or reject a goal collaboration invitation."""
    invitation = get_object_or_404(GoalCollaborationRequest, id=invitation_id, receiver=request.user, status='pending')

    if action == 'accept':
        invitation.status = 'accepted'
        invitation.save()
        invitation.goal.collaborators.add(request.user)
        messages.success(request, f'You have joined the goal: {invitation.goal.title}! 🤝')
    elif action == 'reject':
        invitation.status = 'rejected'
        invitation.save()
        messages.info(request, f'Invitation for {invitation.goal.title} rejected.')

    return redirect('goal_invitations')


@login_required
@user_only
def invite_partner_to_goal(request, goal_id):
    """Invite partner to an existing goal."""
    goal = get_object_or_404(DailyGoal, id=goal_id, user=request.user)
    profile = request.user.profile
    partner = profile.partner

    if not partner:
        messages.error(request, "You don't have a partner to invite.")
        return redirect('goal_detail', goal_id=goal.id)

    if goal.collaborators.filter(id=partner.id).exists():
        messages.warning(request, "Your partner is already a collaborator.")
        return redirect('goal_detail', goal_id=goal.id)

    # Check if a pending invitation already exists
    exists = GoalCollaborationRequest.objects.filter(goal=goal, receiver=partner, status='pending').exists()
    if exists:
        messages.warning(request, "A pending invitation has already been sent.")
    else:
        GoalCollaborationRequest.objects.create(
            goal=goal,
            sender=request.user,
            receiver=partner
        )
        if not goal.is_shared:
            goal.is_shared = True
            goal.save()
        messages.success(request, f'Invitation sent to {partner.username}!')

    return redirect('goal_detail', goal_id=goal.id)


@login_required
@user_only
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
@user_only
def find_partners(request):
    """Search for accountability partners globally."""
    results = []
    form = PartnerSearchForm()

    searched = False
    if request.method == 'POST':
        form = PartnerSearchForm(request.POST)
        if form.is_valid():
            searched = True
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
        'searched': searched,
    })


@login_required
@user_only
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
@user_only
def partner_requests(request):
    """View and manage partner requests."""
    incoming = PartnerRequest.objects.filter(to_user=request.user, status='pending')
    outgoing = PartnerRequest.objects.filter(from_user=request.user, status='pending')

    return render(request, 'core/partner_requests.html', {
        'incoming': incoming,
        'outgoing': outgoing,
    })


@login_required
@user_only
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
@user_only
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
        'partner_profile': partner.profile,
        'partner_goals_today': partner_goals_today,
        'partner_goals_all': partner_goals[:30],
        'total_goals': total,
        'completed_goals': completed,
        'completion_rate': completion_rate,
    })


def _apply_penalty(owner, goal):
    """Apply penalty for a failed goal. Distributed among collaborators if shared."""
    if goal.transactions.filter(type='penalty').exists():
        return  # Already penalized

    goal.status = 'failed'
    goal.save()

    penalty_amount = goal.penalty_amount
    participants = [owner] + list(goal.collaborators.all())
    
    # Update Admin Bank
    system_bank = SystemWallet.get_wallet()
    system_bank.balance += (penalty_amount * len(participants))
    system_bank.save()

    for user in participants:
        profile = user.profile
        profile.wallet_balance -= penalty_amount
        profile.save()

        PenaltyReward.objects.create(
            user=user,
            goal=goal,
            amount=penalty_amount,
            type='penalty',
        )


def _apply_reward(owner, goal):
    """Apply reward (2x penalty) for a completed goal. Distributed among collaborators."""
    if goal.transactions.filter(type='reward').exists():
        return  # Already rewarded

    reward_individual = goal.penalty_amount * 2
    participants = [owner] + list(goal.collaborators.all())
    
    # Update Admin Bank (Payout)
    system_bank = SystemWallet.get_wallet()
    system_bank.balance -= (reward_individual * len(participants))
    system_bank.save()

    for user in participants:
        profile = user.profile
        profile.wallet_balance += reward_individual
        profile.save()

        PenaltyReward.objects.create(
            user=user,
            goal=goal,
            amount=reward_individual,
            type='reward',
        )
