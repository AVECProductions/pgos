from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver

# ----------------------------------------------------------------------------------
# PGOS (SINGLE ROLE & PHONE)
# ----------------------------------------------------------------------------------

class YearlyGoal(models.Model):
    """
    Represents a high-level goal for a given year for one user.
    E.g., "Improve fitness and financial stability in 2025."
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)  # optional
    start_date = models.DateField()  # e.g. Jan 1 of that year
    end_date = models.DateField()    # e.g. Dec 31 of that year
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class QuarterlyGoal(models.Model):
    """
    Breaks a YearlyGoal into smaller quarter-focused goals.
    E.g., "Lose 5 lbs each quarter", "Save $2,000 each quarter", etc.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    yearly_goal = models.ForeignKey(
        'YearlyGoal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True)  # Allows the admin form to work without requiring this field
    quarter = models.PositiveSmallIntegerField()  # 1, 2, 3, or 4
    life_sector = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Q{self.quarter} {self.yearly_goal} - {self.title}"

class KPI(models.Model):
    """
    Short-term measurable linked to a specific quarterly goal.
    E.g., "Run 15 miles per week" or "Save $500 monthly."
    """
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom'),
        # etc.
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quarterly_goal = models.ForeignKey(QuarterlyGoal, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    target_value = models.PositiveIntegerField(blank=True, null=True)
        # e.g. "20 minutes" or "500 dollars" if you store numeric targets
    unit = models.CharField(max_length=50, blank=True)
        # e.g. "minutes", "miles", "dollars"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.frequency})"


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
