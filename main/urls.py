# goals/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),  # home page
    path('quarterly/', views.quarterly_goals_list, name='quarterly_goals_list'),
    path('quarterly/create/', views.quarterly_goal_create, name='quarterly_goal_create'),
]
