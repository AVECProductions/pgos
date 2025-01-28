# goals/forms.py

from django import forms
from .models import QuarterlyGoal

class QuarterlyGoalForm(forms.ModelForm):
    class Meta:
        model = QuarterlyGoal
        fields = ['yearly_goal', 'quarter', 'title', 'description', 'start_date', 'end_date']
        # 'user' is inferred from the current request user, so we won't show it in the form
