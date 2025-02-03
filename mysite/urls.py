from django.contrib import admin
from django.urls import path, include
from main.views import *
from decouple import config

urlpatterns = [
    path(config('ADMIN_URL'), admin.site.urls),
    path('', home_view, name='home'),
    path('', include('main.urls')),  # directs root paths to "goals/urls.py"
    path('accounts/login/', member_login_view, name='login'),
    path('accounts/logout/', member_logout_view, name='logout'),
    path('member-profile/', member_profile, name='member_profile'),
    path('quarterly-goals/', quarterly_goals_list, name='quarterly_goals_list'),
    path('coming-soon/', coming_soon, name='coming_soon'),
]