# main/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.timezone import localtime, now, timedelta, make_aware
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import QuarterlyGoal
from django.contrib import messages
from collections import defaultdict

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
