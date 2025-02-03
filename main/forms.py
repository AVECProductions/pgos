from django import forms
from .models import QuarterlyGoal
from django.utils.timezone import now

class QuarterlyGoalForm(forms.ModelForm):
    class Meta:
        model = QuarterlyGoal
        fields = ['life_sector', 'description']  # Only display 'title' and 'description'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Modify the description field to allow one-line input
        self.fields['description'].widget = forms.TextInput(attrs={
            'placeholder': 'Enter a brief description...',
            'style': 'width: 100%;',
        })
