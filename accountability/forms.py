from django import forms
from .models import Goal, DailyUpdate

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['title', 'description', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }

class DailyUpdateForm(forms.ModelForm):
    class Meta:
        model = DailyUpdate
        fields = ['achievements', 'bottlenecks', 'plan_for_tomorrow', 'mood_rating']
