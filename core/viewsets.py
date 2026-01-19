"""
Django REST Framework viewsets for core models.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone

from .models import Centre, Child, VisitType, Visit, CaseloadAssignment
from .serializers import (
    CentreSerializer, ChildListSerializer, ChildDetailSerializer,
    VisitTypeSerializer, VisitSerializer, VisitCreateSerializer,
    CaseloadAssignmentSerializer
)
from .permissions import (
    IsStaffMember, IsSupervisorOrAdmin, CanEditVisit, CanAccessReports
)


class CentreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Centre model.
    All authenticated users can view centres.
    Only supervisors and admins can create/edit/delete.
    """
    
    queryset = Centre.objects.all()
    serializer_class = CentreSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'city']
    search_fields = ['name', 'city', 'contact_name']
    ordering_fields = ['name', 'city']
    ordering = ['name']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSupervisorOrAdmin]
        else:
            permission_classes = [IsStaffMember]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active centres."""
        centres = self.queryset.filter(status='active')
        serializer = self.get_serializer(centres, many=True)
        return Response(serializer.data)


class ChildViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Child model.
    All authenticated users can view children.
    Supervisors and admins can create/edit/delete.
    """
    
    queryset = Child.objects.select_related('centre', 'created_by', 'updated_by').prefetch_related('caseload_assignments')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'centre']
    search_fields = ['first_name', 'last_name', 'guardian1_name']
    ordering_fields = ['last_name', 'first_name', 'date_of_birth', 'created_at']
    ordering = ['last_name', 'first_name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChildListSerializer
        return ChildDetailSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSupervisorOrAdmin]
        else:
            permission_classes = [IsStaffMember]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def my_caseload(self, request):
        """
        Get children in the current staff member's caseload.
        Includes primary assignments and children they've visited.
        """
        user = request.user
        
        # Get children from primary caseload assignments
        primary_caseload = Child.objects.filter(
            caseload_assignments__staff=user,
            caseload_assignments__is_primary=True,
            caseload_assignments__unassigned_at__isnull=True
        ).distinct()
        
        # Get unique children from user's visits (including non-caseload)
        visited_children = Child.objects.filter(
            visits__staff=user
        ).distinct()
        
        # Combine and exclude discharged children unless they have an active assignment
        children = (primary_caseload | visited_children).filter(
            Q(status__in=['active', 'on_hold', 'non_caseload']) |
            Q(caseload_assignments__staff=user, caseload_assignments__unassigned_at__isnull=True)
        ).distinct()
        
        serializer = ChildListSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def non_caseload(self, request):
        """Get all non-caseload children."""
        children = self.queryset.filter(status='non_caseload')
        serializer = ChildListSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def all_children(self, request):
        """Get all children (for staff with view-all permission)."""
        serializer = ChildListSerializer(self.queryset, many=True)
        return Response(serializer.data)


class VisitTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly ViewSet for VisitType model.
    All authenticated users can view visit types.
    """
    
    queryset = VisitType.objects.filter(is_active=True)
    serializer_class = VisitTypeSerializer
    permission_classes = [IsStaffMember]
    ordering = ['name']


class VisitViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Visit model.
    Staff can create and edit their own visits.
    Supervisors and admins can edit all visits.
    """
    
    queryset = Visit.objects.select_related('child', 'staff', 'centre', 'visit_type')
    serializer_class = VisitSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['child', 'staff', 'centre', 'visit_type', 'visit_date', 'flagged_for_review']
    search_fields = ['child__first_name', 'child__last_name', 'notes']
    ordering_fields = ['visit_date', 'start_time', 'created_at']
    ordering = ['-visit_date', '-start_time']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return VisitCreateSerializer
        return VisitSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update']:
            permission_classes = [CanEditVisit]
        elif self.action == 'destroy':
            permission_classes = [IsSupervisorOrAdmin]
        else:
            permission_classes = [IsStaffMember]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """Set staff to current user if not specified."""
        if 'staff' not in serializer.validated_data:
            serializer.save(staff=self.request.user)
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def my_visits(self, request):
        """Get visits for the current user."""
        visits = self.queryset.filter(staff=request.user)
        
        # Apply date filtering if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            visits = visits.filter(visit_date__gte=start_date)
        if end_date:
            visits = visits.filter(visit_date__lte=end_date)
        
        serializer = self.get_serializer(visits, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def flagged(self, request):
        """Get visits flagged for review (>7 hours)."""
        visits = self.queryset.filter(flagged_for_review=True)
        serializer = self.get_serializer(visits, many=True)
        return Response(serializer.data)


class CaseloadAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CaseloadAssignment model.
    Only supervisors and admins can manage caseload assignments.
    """
    
    queryset = CaseloadAssignment.objects.select_related('child', 'staff', 'assigned_by')
    serializer_class = CaseloadAssignmentSerializer
    permission_classes = [IsSupervisorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['child', 'staff', 'is_primary']
    ordering_fields = ['assigned_at', 'unassigned_at']
    ordering = ['-assigned_at']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active caseload assignments."""
        assignments = self.queryset.filter(unassigned_at__isnull=True)
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_reassign(self, request):
        """
        Bulk reassign caseload from one staff member to another.
        
        Request body:
        {
            "from_staff": <staff_id>,
            "to_staff": <staff_id>,
            "child_ids": [<child_id>, ...] (optional, defaults to all)
        }
        """
        from_staff_id = request.data.get('from_staff')
        to_staff_id = request.data.get('to_staff')
        child_ids = request.data.get('child_ids', [])
        
        if not from_staff_id or not to_staff_id:
            return Response(
                {'error': 'Both from_staff and to_staff are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get active assignments
        assignments = self.queryset.filter(
            staff_id=from_staff_id,
            unassigned_at__isnull=True
        )
        
        # Filter by specific children if provided
        if child_ids:
            assignments = assignments.filter(child_id__in=child_ids)
        
        # Unassign from old staff
        now = timezone.now()
        assignments.update(unassigned_at=now)
        
        # Create new assignments to new staff
        from accounts.models import User
        to_staff = User.objects.get(pk=to_staff_id)
        
        new_assignments = []
        for old_assignment in assignments:
            new_assignment = CaseloadAssignment.objects.create(
                child=old_assignment.child,
                staff=to_staff,
                is_primary=old_assignment.is_primary,
                assigned_by=request.user
            )
            new_assignments.append(new_assignment)
        
        # Log bulk operation in audit
        from audit.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            entity_type='CaseloadAssignment',
            entity_id=0,
            action='bulk_update',
            metadata={
                'operation': 'bulk_reassign',
                'from_staff': from_staff_id,
                'to_staff': to_staff_id,
                'count': len(new_assignments),
                'children': [a.child.full_name for a in new_assignments]
            }
        )
        
        serializer = self.get_serializer(new_assignments, many=True)
        return Response({
            'message': f'Successfully reassigned {len(new_assignments)} children',
            'assignments': serializer.data
        })
