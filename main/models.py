from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords
from django.db.models import F

# ----------------------------------------------------------------------------------
# PGOS (SINGLE ROLE & PHONE)
# ----------------------------------------------------------------------------------

class YearlyGoal(models.Model):
    """
    Represents a high-level goal for a given year for one user.
    E.g., "Improve fitness and financial stability in 2025."
    """
    LIFE_SECTORS = [
        ('other', 'Other'),
        ('health', 'Health & Fitness'),
        ('career', 'Career & Work'),
        ('relationships', 'Relationships'),
        ('personal', 'Personal Growth'),
        ('finance', 'Finance'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    life_sector = models.CharField(max_length=20, choices=LIFE_SECTORS, default='other')
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s {self.get_life_sector_display()} Goal"

    def clean(self):
        # Add validation to ensure end_date is after start_date
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError('End date must be after start date')

    def get_quarterly_goals(self):
        """API helper to get related quarterly goals"""
        return self.quarterlygoal_set.all()

class QuarterlyGoal(models.Model):
    """
    Breaks a YearlyGoal into smaller quarter-focused goals.
    E.g., "Lose 5 lbs each quarter", "Save $2,000 each quarter", etc.
    """
    LIFE_SECTORS = [
        ('other', 'Other'),
        ('health', 'Health & Fitness'),
        ('career', 'Career & Work'),
        ('relationships', 'Relationships'),
        ('personal', 'Personal Growth'),
        ('finance', 'Finance'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    yearly_goal = models.ForeignKey(YearlyGoal, on_delete=models.SET_NULL, null=True, blank=True)
    life_sector = models.CharField(max_length=20, choices=LIFE_SECTORS, default='other')
    description = models.TextField()
    quarter = models.IntegerField(choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')])
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s Q{self.quarter} {self.life_sector} Goal"

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError('End date must be after start date')
        
        # Validate quarter value
        if not 1 <= self.quarter <= 4:
            raise ValidationError('Quarter must be between 1 and 4')

    def get_kpis(self):
        """API helper to get related KPIs"""
        return self.kpi_set.all()

    def get_progress(self):
        """Calculate and return progress metrics for this goal"""
        kpis = self.get_kpis()
        return {
            'total_kpis': kpis.count(),
            'completed_kpis': kpis.filter(records__value__gte=F('target_value')).distinct().count()
        }

class KPI(models.Model):
    """
    Key Performance Indicator (KPI) for tracking progress on goals
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quarterly_goal = models.ForeignKey(
        QuarterlyGoal, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    target_value = models.FloatField(default=0)
    unit = models.CharField(max_length=50, default='units')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'KPI'
        verbose_name_plural = 'KPIs'

    def __str__(self):
        return f"{self.name} ({self.frequency})"

    def get_recent_records(self):
        """Return recent KPI records"""
        return self.records.all().order_by('-entry_date')[:7]

    def get_progress(self):
        """Calculate and return progress metrics"""
        records = self.get_recent_records()
        if not records:
            return {
                'current_value': 0,
                'target_value': self.target_value,
                'percentage': 0
            }
        latest = records[0]
        return {
            'current_value': latest.value,
            'target_value': self.target_value,
            'percentage': (latest.value / self.target_value) * 100 if self.target_value else 0
        }

class KPIRecord(models.Model):
    """
    Records an instance of completing or progressing towards a KPI on a particular date.
    E.g., "On 2025-01-15, user did 3 out of 5 miles of running."
    """
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name='records')
    entry_date = models.DateField()
    value = models.FloatField(default=0)
        # if you track partial values (miles, minutes, etc.)
    notes = models.TextField(blank=True)  # optional reflection or details

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('kpi', 'entry_date')

    def __str__(self):
        return f"{self.kpi.name} on {self.entry_date}: {self.value}"

    def clean(self):
        # Add validation for value based on KPI type
        if self.value < 0:
            raise ValidationError('Value cannot be negative')


# ----------------------------------------------------------------------------------
# USER PROFILE (SINGLE ROLE & PHONE)
# ----------------------------------------------------------------------------------
class UserProfile(models.Model):
    """
    Extends the built-in User model with a single role and phone.
    """
    class Meta:
        db_table = "user_profile"

    ROLE_CHOICES = (
        ('member', 'Member'),
        ('admin', 'Admin'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="public"  # or "member", depending on your default
    )
    phone = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    def has_minimum_role(self, required_role):
        """
        Utility that returns True if this user's role is >= the required role in hierarchy.
        """
        role_priority = {
            'member': 1,
            'admin': 2,
        }
        return role_priority[self.role] >= role_priority[required_role]


# ----------------------------------------------------------------------------------
# CREATE / SAVE USER PROFILE SIGNALS
# ----------------------------------------------------------------------------------
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


# Add these new models to the existing models.py

class Vision(models.Model):
    """
    Represents a user's vision statement and core values
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username}'s Vision - {self.title}"

class RICHItem(models.Model):
    """
    Represents items in the RICH system (Responsibilities, Interests, Commitments, Hobbies)
    """
    RICH_TYPES = (
        ('responsibility', 'Responsibility'),
        ('interest', 'Interest'),
        ('commitment', 'Commitment'),
        ('hobby', 'Hobby'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rich_type = models.CharField(max_length=20, choices=RICH_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    retired = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['rich_type', 'title']

    def __str__(self):
        return f"{self.get_rich_type_display()}: {self.title}"

class JournalEntry(models.Model):
    """
    Represents a journal entry with rich text content
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content_html = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Journal entries'

    def __str__(self):
        return f"{self.user.username}'s Entry - {self.title}"
