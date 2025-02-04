from rest_framework import serializers
from .models import YearlyGoal, QuarterlyGoal, KPI, KPIRecord, UserProfile, Vision, RICHItem, JournalEntry
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'role', 'phone']
        read_only_fields = ['user']

class KPIRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = KPIRecord
        fields = ['id', 'kpi', 'entry_date', 'value', 'notes', 'created_at']
        read_only_fields = ['created_at']

class KPISerializer(serializers.ModelSerializer):
    recent_records = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = KPI
        fields = ['id', 'quarterly_goal', 'name', 'description', 'frequency',
                 'target_value', 'unit', 'recent_records', 'progress']
        read_only_fields = ['user']
        extra_kwargs = {
            'name': {'required': True},
            'description': {'required': True},
            'frequency': {'required': True},
            'target_value': {'required': True},
            'unit': {'required': True},
        }

    def get_recent_records(self, obj):
        records = obj.get_recent_records()
        return KPIRecordSerializer(records, many=True).data

    def get_progress(self, obj):
        return obj.get_progress()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class YearlyGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = YearlyGoal
        fields = ['id', 'user', 'description', 'life_sector', 
                 'start_date', 'end_date']
        read_only_fields = ['user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class QuarterlyGoalSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    yearly_goal = YearlyGoalSerializer(read_only=True)

    class Meta:
        model = QuarterlyGoal
        fields = ['id', 'yearly_goal', 'life_sector', 'description', 
                 'quarter', 'start_date', 'end_date', 'progress']

    def get_progress(self, obj):
        return obj.get_progress()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class VisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vision
        fields = ['id', 'title', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class RICHItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RICHItem
        fields = ['id', 'title', 'description', 'rich_type', 'created_at', 'retired']
        read_only_fields = ['created_at']

class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = ['id', 'content_html', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'password')
        
    def validate(self, attrs):
        # Add custom validation here
        print("Received data:", attrs)  # Add this for debugging
        return super().validate(attrs)
        
    def create(self, validated_data):
        print("Creating user with data:", validated_data)  # Add this for debugging
        user = User.objects.create_user(**validated_data)
        # Add any additional setup for new users here
        return user 