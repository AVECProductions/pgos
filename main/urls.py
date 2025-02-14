# goals/urls.py

from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.routers import DefaultRouter
from .views import (
    YearlyGoalViewSet, QuarterlyGoalViewSet,
    KPIViewSet, KPIRecordViewSet, UserProfileViewSet,
    DashboardViewSet, VisionViewSet, RICHItemViewSet,
    JournalEntryViewSet, journal_webhook
)

router = DefaultRouter()
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'vision', VisionViewSet, basename='vision')
router.register(r'rich', RICHItemViewSet, basename='rich')
router.register(r'yearly-goals', YearlyGoalViewSet, basename='yearly-goal')
router.register(r'quarterly-goals', QuarterlyGoalViewSet, basename='quarterly-goal')
router.register(r'kpis', KPIViewSet, basename='kpi')
router.register(r'kpi-records', KPIRecordViewSet, basename='kpi-record')
router.register(r'users/profile', UserProfileViewSet, basename='user-profile')
router.register(r'journal', JournalEntryViewSet, basename='journal')

urlpatterns = [
    # JWT Authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Group all API endpoints under /api/
    path('api/', include([
        # Router URLs
        path('', include(router.urls)),
        # Webhook endpoint
        path('webhooks/journal/', journal_webhook, name='journal-webhook'),
    ])),
]