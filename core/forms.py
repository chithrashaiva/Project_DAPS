from django import forms
from .models import DailyGoal, ProgressLog


class GoalForm(forms.ModelForm):
    class Meta:
        model = DailyGoal
        fields = ('title', 'description', 'deadline', 'phase', 'penalty_amount')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'What do you want to accomplish today?',
                'id': 'goal-title',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Describe your goal in detail...',
                'rows': 3,
                'id': 'goal-description',
            }),
            'deadline': forms.DateTimeInput(attrs={
                'class': 'form-input',
                'type': 'datetime-local',
                'id': 'goal-deadline',
            }),
            'phase': forms.Select(attrs={
                'class': 'form-input',
                'id': 'goal-phase',
            }),
            'penalty_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Penalty amount if failed ($)',
                'min': '0',
                'step': '0.01',
                'id': 'goal-penalty',
            }),
        }


class ProgressLogForm(forms.ModelForm):
    class Meta:
        model = ProgressLog
        fields = ('note',)
        widgets = {
            'note': forms.Textarea(attrs={
                'class': 'form-input',
                'placeholder': 'Add a progress update...',
                'rows': 2,
                'id': 'progress-note',
            })
        }


class PartnerSearchForm(forms.Form):
    query = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by username or email...',
            'id': 'partner-search',
        })
    )
