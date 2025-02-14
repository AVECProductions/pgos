# main/views.py
from django.utils.timezone import localtime, now, timedelta, make_aware
from .models import QuarterlyGoal, Vision, RICHItem, JournalEntry

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import YearlyGoal, KPI, KPIRecord, UserProfile
from .serializers import (YearlyGoalSerializer, QuarterlyGoalSerializer,
                         KPISerializer, KPIRecordSerializer, UserProfileSerializer,
                         VisionSerializer, RICHItemSerializer, JournalEntrySerializer)
from django.db.models import Count
from django.utils import timezone
from django.contrib.auth.models import User
import logging
from rest_framework.permissions import AllowAny
from django.conf import settings
import hmac
import hashlib
import json
from django.http import HttpResponse

logger = logging.getLogger(__name__)

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
        return KPIRecord.objects.filter(kpi__user=self.request.user)

    def create(self, request, *args, **kwargs):
        logger.info(f"Received KPI record data: {request.data}")
        
        # Validate that the KPI belongs to the user
        try:
            kpi = KPI.objects.get(id=request.data.get('kpi'), user=request.user)
        except KPI.DoesNotExist:
            return Response(
                {"error": "KPI not found or does not belong to user"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating KPI record: {str(e)}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        serializer.save()

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
        # Add recent KPI records
        for record in KPIRecord.objects.filter(
            kpi__user=user, 
            created_at__gte=last_month
        ).order_by('-created_at')[:3]:  # Only get last 3 records
            recent_activity.append({
                'id': f'kpi_{record.id}',
                'date': record.created_at,
                'description': f'Tracked KPI {record.kpi.name}: {record.value} {record.kpi.unit}'
            })

        return Response({
            'stats': stats,
            'recent_activity': recent_activity  # Will only contain last 3 activities
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
        queryset = JournalEntry.objects.filter(user=self.request.user).order_by('-created_at')  # Order first
        limit = self.request.query_params.get('limit', None)
        if limit is not None:
            try:
                limit = int(limit)
                queryset = queryset[:limit]  # Then slice
            except ValueError:
                pass
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def journal_webhook(request):
    """Webhook endpoint for receiving journal entries from ElevenLabs agent."""
    # Add detailed logging
    logger.info(f"Received webhook request from: {request.META.get('REMOTE_ADDR')}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    # Get the raw body for signature verification
    raw_body = request.body.decode('utf-8')
    logger.info(f"Request body: {raw_body}")
    
    # Verify webhook signature if provided
    signature = request.headers.get('X-Webhook-Signature')
    if signature and hasattr(settings, 'ELEVENLABS_WEBHOOK_SECRET'):
        expected_signature = hmac.new(
            settings.ELEVENLABS_WEBHOOK_SECRET.encode(),
            raw_body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            logger.error("Invalid signature")
            return HttpResponse('Invalid signature', status=401)
    
    try:
        data = json.loads(raw_body)
        content_html = data.get('content_html')
        
        if not content_html:
            logger.error("Missing content_html in payload")
            return HttpResponse('Missing required fields', status=400)
        
        try:
            # Use user ID 1 for now (update this based on your needs)
            user_id = 1
            entry = JournalEntry.objects.create(
                user_id=user_id,
                content_html=content_html
            )
            logger.info(f"Created journal entry: {entry.id}")
            return HttpResponse('Journal entry created', status=201)
            
        except Exception as e:
            logger.error(f"Error creating journal entry: {str(e)}")
            return HttpResponse('Error creating journal entry', status=500)
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {str(e)}")
        return HttpResponse('Invalid JSON payload', status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return HttpResponse('Internal server error', status=500)
