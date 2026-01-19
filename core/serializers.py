"""
Django REST Framework serializers for core models.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Centre, Child, VisitType, Visit, CaseloadAssignment
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (basic info only)."""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email', 'role']
        read_only_fields = ['id', 'username', 'role']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class CentreSerializer(serializers.ModelSerializer):
    """Serializer for Centre model."""
    
    full_address = serializers.ReadOnlyField()
    active_children_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Centre
        fields = [
            'id', 'name', 'address_line1', 'address_line2', 'city', 'province',
            'postal_code', 'full_address', 'phone', 'contact_name', 'contact_email',
            'status', 'notes', 'active_children_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_active_children_count(self, obj):
        return obj.children.filter(status='active').count()


class CaseloadAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for CaseloadAssignment model."""
    
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    child_name = serializers.CharField(source='child.full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = CaseloadAssignment
        fields = [
            'id', 'child', 'child_name', 'staff', 'staff_name',
            'is_primary', 'assigned_at', 'unassigned_at',
            'assigned_by', 'assigned_by_name', 'is_active'
        ]
        read_only_fields = ['id', 'assigned_at', 'assigned_by']
    
    def get_is_active(self, obj):
        return obj.unassigned_at is None
    
    def create(self, validated_data):
        # Set assigned_by from request context
        request = self.context.get('request')
        if request and request.user:
            validated_data['assigned_by'] = request.user
        return super().create(validated_data)


class ChildListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for child lists."""
    
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    centre_name = serializers.CharField(source='centre.name', read_only=True)
    primary_staff = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Child
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'age',
            'date_of_birth', 'centre', 'centre_name', 'status',
            'status_display', 'primary_staff', 'start_date'
        ]
    
    def get_primary_staff(self, obj):
        staff = obj.get_primary_staff()
        if staff:
            return {
                'id': staff.id,
                'name': staff.get_full_name()
            }
        return None


class ChildDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for child records."""
    
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    centre_details = CentreSerializer(source='centre', read_only=True)
    caseload_staff = CaseloadAssignmentSerializer(source='caseload_assignments', many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Child
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'age', 'date_of_birth',
            'address_line1', 'address_line2', 'city', 'province', 'postal_code',
            'guardian1_name', 'guardian1_phone', 'guardian1_email',
            'guardian2_name', 'guardian2_phone', 'guardian2_email',
            'centre', 'centre_details', 'status', 'status_display',
            'start_date', 'end_date', 'notes',
            'caseload_staff', 'created_at', 'updated_at',
            'created_by', 'created_by_name', 'updated_by', 'updated_by_name'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by', 'updated_by'
        ]


class VisitTypeSerializer(serializers.ModelSerializer):
    """Serializer for VisitType model."""
    
    class Meta:
        model = VisitType
        fields = ['id', 'name', 'description', 'is_active']
        read_only_fields = ['id']


class VisitSerializer(serializers.ModelSerializer):
    """Serializer for Visit model."""
    
    child_name = serializers.CharField(source='child.full_name', read_only=True)
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    centre_name = serializers.CharField(source='centre.name', read_only=True)
    visit_type_name = serializers.CharField(source='visit_type.name', read_only=True)
    duration_hours = serializers.ReadOnlyField()
    duration_decimal = serializers.ReadOnlyField()
    
    class Meta:
        model = Visit
        fields = [
            'id', 'child', 'child_name', 'staff', 'staff_name',
            'centre', 'centre_name', 'visit_date', 'start_time', 'end_time',
            'visit_type', 'visit_type_name', 'location_description', 'notes',
            'duration_hours', 'duration_decimal', 'flagged_for_review',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'flagged_for_review', 'created_at', 'updated_at', 'centre']
    
    def validate(self, data):
        """Validate visit data."""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time.'
                })
        
        return data
    
    def create(self, validated_data):
        """
        Create visit with automatic centre snapshot from child's current centre.
        """
        child = validated_data['child']
        
        # Capture child's current centre as historical snapshot (only if not provided)
        if 'centre' not in validated_data:
            validated_data['centre'] = child.centre
        
        # Create the visit
        visit = super().create(validated_data)
        
        return visit
    
    def to_representation(self, instance):
        """Add warning for visits over 7 hours."""
        representation = super().to_representation(instance)
        
        if instance.flagged_for_review:
            representation['warning'] = 'Visit duration exceeds 7 hours and is flagged for review'
        
        return representation


class VisitCreateSerializer(serializers.ModelSerializer):
    """
    Specialized serializer for creating visits via mobile interface.
    Simplified fields for easier mobile data entry.
    """
    
    class Meta:
        model = Visit
        fields = [
            'child', 'staff', 'visit_date', 'start_time', 'end_time',
            'visit_type', 'location_description', 'notes'
        ]
    
    def validate(self, data):
        """Validate visit data."""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time.'
                })
        
        return data
    
    def create(self, validated_data):
        """Create visit with automatic centre snapshot."""
        child = validated_data['child']
        validated_data['centre'] = child.centre
        
        visit = Visit.objects.create(**validated_data)
        return visit
