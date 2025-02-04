# main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.timezone import localtime, now, timedelta, make_aware
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import QuarterlyGoal, Vision, RICHItem, JournalEntry
from django.contrib import messages
from collections import defaultdict
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import YearlyGoal, KPI, KPIRecord, UserProfile
from .serializers import (YearlyGoalSerializer, QuarterlyGoalSerializer,
                         KPISerializer, KPIRecordSerializer, UserProfileSerializer,
                         VisionSerializer, RICHItemSerializer, JournalEntrySerializer)
from django.db.models import Count
from django.utils import timezone
from django.contrib.auth.models import User

# Decorators
def role_required(role):
    """
    A decorator restricting access to a particular role
    (e.g., operator, admin). If mismatch, returns 403.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.profile.has_minimum_role(role):
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("You do not have permission to access this page.")
        return _wrapped_view
    return decorator


# ------------------------------------------
# HOME & AUTHENTICATION
# ------------------------------------------
@login_required
def home_view(request):
    """
    Home page, with buttons for "Yearly," "Quarterly," and "KPI"
    (though only "Quarterly" will be functional for now).
    """
    return render(request, 'main/home.html')


@login_required
def quarterly_goals_list(request):
    """
    Displays the user's quarterly goals grouped by life sector.
    """
    user = request.user
    goals = QuarterlyGoal.objects.filter(user=user).order_by('life_sector', 'start_date')

    # Group goals by life_sector
    grouped_goals = defaultdict(list)
    for goal in goals:
        grouped_goals[goal.life_sector].append(goal)

    # Debugging output
    print(f"Goals for user {user.username}: {goals}")
    print(f"Grouped goals: {grouped_goals}")

    return render(request, 'quarterly/quarterly_goals_list.html', {'grouped_goals': grouped_goals})

# goals/views.py (continued)

from .forms import QuarterlyGoalForm

@login_required
def quarterly_goal_create(request):
    """
    Create a new Quarterly Goal for the active quarter.
    """
    # Determine the active quarter
    current_date = now().date()
    current_month = current_date.month
    if 1 <= current_month <= 3:
        quarter = 1
        end_date = current_date.replace(month=3, day=31)
    elif 4 <= current_month <= 6:
        quarter = 2
        end_date = current_date.replace(month=6, day=30)
    elif 7 <= current_month <= 9:
        quarter = 3
        end_date = current_date.replace(month=9, day=30)
    else:
        quarter = 4
        end_date = current_date.replace(month=12, day=31)

    start_date = current_date

    if request.method == 'POST':
        form = QuarterlyGoalForm(request.POST)
        if form.is_valid():
            new_goal = form.save(commit=False)
            new_goal.user = request.user
            new_goal.quarter = quarter
            new_goal.start_date = start_date
            new_goal.end_date = end_date
            new_goal.yearly_goal = None  # Set yearly goal to null for now
            new_goal.save()
            messages.success(request, "Quarterly Goal created!")
            return redirect('quarterly_goals_list')
    else:
        form = QuarterlyGoalForm()

    context = {
        'form': form,
        'quarter': quarter,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'quarterly/quarterly_goal_create.html', context)



def member_login_view(request):
    """
    Standard Django authentication (username/password).
    """
    error = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('home')
        else:
            error = "Invalid credentials. Please try again."

    return render(request, 'credential/member_login.html', {'error': error})

@login_required
def member_logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def member_profile(request):
    """
    Display/Edit the member's profile.
    """
    if request.user.profile.role == "public":
        return HttpResponseForbidden("You are not authorized to access this page.")

    if request.method == "POST":
        # Update Django's built-in User fields
        user = request.user
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.email = request.POST.get("email", user.email)
        user.save()

        # Update your Profile model fields
        user_profile = user.profile
        user_profile.phone = request.POST.get("phone", user_profile.phone)
        user_profile.save()

        messages.success(request, "Your profile has been updated.")
        return redirect("member_profile")

    context = {
        "user": request.user,  # so template can do {{ user.first_name }}, etc.
    }
    return render(request, "member/profile.html", context)

def coming_soon(request):
    return render(request, 'main/coming_soon.html')

class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def list(self, request):
        """Override list to return only the current user's profile"""
        serializer = self.get_serializer(request.user.profile)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Override retrieve to ensure users can only access their own profile"""
        if str(request.user.id) != pk:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, pk)

class YearlyGoalViewSet(viewsets.ModelViewSet):
    serializer_class = YearlyGoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['title', 'description']
    filterset_fields = ['start_date', 'end_date']

    def get_queryset(self):
        return YearlyGoal.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        goal = self.get_object()
        history = []
        for record in goal.history.all():
            changes = {}
            if record.prev_record:
                delta = record.diff_against(record.prev_record)
                changes = {
                    change.field: {
                        'from': change.old,
                        'to': change.new
                    }
                    for change in delta.changes
                }
            
            history.append({
                'user': record.history_user.username if record.history_user else 'System',
                'created_at': record.history_date,
                'changes': changes
            })
        return Response(history)

class QuarterlyGoalViewSet(viewsets.ModelViewSet):
    serializer_class = QuarterlyGoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['life_sector', 'description']
    filterset_fields = ['quarter', 'yearly_goal']

    def get_queryset(self):
        return QuarterlyGoal.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        goal = self.get_object()
        history = []
        for record in goal.history.all():
            changes = {}
            if record.prev_record:
                delta = record.diff_against(record.prev_record)
                changes = {
                    change.field: {
                        'from': change.old,
                        'to': change.new
                    }
                    for change in delta.changes
                }
            
            history.append({
                'user': record.history_user.username if record.history_user else 'System',
                'created_at': record.history_date,
                'changes': changes
            })
        return Response(history)

class KPIViewSet(viewsets.ModelViewSet):
    serializer_class = KPISerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['frequency', 'quarterly_goal']

    def get_queryset(self):
        print(f"Fetching KPIs for user {self.request.user.username}")  # Add debug print
        queryset = KPI.objects.filter(user=self.request.user)
        print(f"Found {queryset.count()} KPIs")  # Add debug print
        return queryset

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        kpi = self.get_object()
        return Response({
            'progress': kpi.get_progress(),
            'recent_records': KPIRecordSerializer(
                kpi.get_recent_records(), many=True).data
        })

class KPIRecordViewSet(viewsets.ModelViewSet):
    serializer_class = KPIRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['entry_date', 'kpi']

    def get_queryset(self):
        return KPIRecord.objects.filter(kpi__quarterly_goal__user=self.request.user)

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user = request.user
        now = timezone.now()
        last_month = now - timedelta(days=30)

        stats = {
            'activeGoals': QuarterlyGoal.objects.filter(user=user, end_date__gte=now).count(),
            'kpisTracked': KPI.objects.filter(user=user).count(),
            'journalEntries': JournalEntry.objects.filter(user=user).count(),
            'richItems': RICHItem.objects.filter(user=user, retired=False).count(),
        }

        recent_activity = []
        # Add recent goals
        for goal in QuarterlyGoal.objects.filter(user=user, created_at__gte=last_month):
            recent_activity.append({
                'id': f'goal_{goal.id}',
                'date': goal.created_at,
                'description': f'Created new quarterly goal: {goal.life_sector}'
            })
        # Add recent KPI records
        for record in KPIRecord.objects.filter(kpi__user=user, created_at__gte=last_month):
            recent_activity.append({
                'id': f'kpi_{record.id}',
                'date': record.created_at,
                'description': f'Tracked KPI {record.kpi.name}: {record.value} {record.kpi.unit}'
            })
        # Sort by date
        recent_activity.sort(key=lambda x: x['date'], reverse=True)

        return Response({
            'stats': stats,
            'recent_activity': recent_activity[:10]  # Last 10 activities
        })

class VisionViewSet(viewsets.ModelViewSet):
    serializer_class = VisionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Vision.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class RICHItemViewSet(viewsets.ModelViewSet):
    serializer_class = RICHItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['rich_type', 'retired']
    search_fields = ['title', 'description']

    def get_queryset(self):
        return RICHItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class JournalEntryViewSet(viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['created_at']
    search_fields = ['title', 'content_html']

    def get_queryset(self):
        return JournalEntry.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
