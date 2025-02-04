from django.contrib import admin
from .models import (
    YearlyGoal, QuarterlyGoal, KPI, KPIRecord, 
    UserProfile, Vision, RICHItem, JournalEntry
)

@admin.register(Vision)
class VisionAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'created_at', 'updated_at')
    search_fields = ('title', 'description')
    list_filter = ('created_at', 'updated_at')

@admin.register(RICHItem)
class RICHItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'rich_type', 'created_at', 'retired')
    list_filter = ('rich_type', 'retired', 'created_at')
    search_fields = ('title', 'description')

@admin.register(YearlyGoal)
class YearlyGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'life_sector', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
    search_fields = ('life_sector', 'description')

@admin.register(QuarterlyGoal)
class QuarterlyGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'yearly_goal', 'quarter', 'life_sector')
    list_filter = ('quarter', 'start_date', 'end_date')
    search_fields = ('life_sector', 'description')

@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'frequency', 'target_value', 'unit')
    list_filter = ('frequency', 'created_at')
    search_fields = ('name', 'description')

@admin.register(KPIRecord)
class KPIRecordAdmin(admin.ModelAdmin):
    list_display = ('kpi', 'entry_date', 'value')
    list_filter = ('entry_date',)
    search_fields = ('notes',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'phone')

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    list_filter = ['user', 'created_at']
    search_fields = ['content_html']
    ordering = ['-created_at']
