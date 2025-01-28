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
    Displays a list of the current user's quarterly goals.
    """
    user = request.user
    goals = QuarterlyGoal.objects.filter(user=user).order_by('start_date')

    context = {
        'goals': goals
    }
    return render(request, 'quarterly/quarterly_goals_list.html', context)

# goals/views.py (continued)

from .forms import QuarterlyGoalForm

@login_required
def quarterly_goal_create(request):
    """
    Shows a form to create a new QuarterlyGoal and saves it on POST.
    """
    if request.method == 'POST':
        form = QuarterlyGoalForm(request.POST)
        if form.is_valid():
            # Create an instance but don't save yet
            new_goal = form.save(commit=False)
            # Assign the user to the new goal
            new_goal.user = request.user
            new_goal.save()

            messages.success(request, "Quarterly Goal created!")
            return redirect('quarterly_goals_list')
    else:
        form = QuarterlyGoalForm()

    return render(request, 'quarterly/quarterly_goal_create.html', {'form': form})



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
