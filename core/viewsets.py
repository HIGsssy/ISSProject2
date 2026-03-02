"""
Django REST Framework viewsets for core models.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone

from .models import Centre, Child, VisitType, Visit, CaseloadAssignment, CaseNote
from .serializers import (
    CentreSerializer, ChildListSerializer, ChildDetailSerializer, ChildCreateSerializer,
    VisitTypeSerializer, VisitSerializer, VisitCreateSerializer,
    CaseloadAssignmentSerializer, CaseNoteSerializer
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
    filterset_fields = ['overall_status', 'caseload_status', 'on_hold', 'centre']
    search_fields = ['first_name', 'last_name', 'guardian1_name']
    ordering_fields = ['last_name', 'first_name', 'date_of_birth', 'created_at']
    ordering = ['last_name', 'first_name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChildListSerializer
        elif self.action == 'create':
            return ChildCreateSerializer
        return ChildDetailSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            # Only supervisors and admins can edit/delete
            permission_classes = [IsSupervisorOrAdmin]
        else:
            # Staff, supervisors, and admins can create and view
            permission_classes = [IsStaffMember]
        return [permission() for permission in permission_classes]
    
    def perform_update(self, serializer):
        """Track who updated the child."""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_caseload(self, request):
        """
        Get children in the current staff member's caseload.
        Only includes actual caseload assignments, not visits.
        Supervisors/admins should not have caseloads.
        """
        user = request.user
        
        # Supervisors and admins should not have caseloads
        if hasattr(user, 'role') and user.role in ['supervisor', 'admin']:
            return Response({'detail': 'Supervisors and admins do not have caseloads.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get children from caseload assignments
        children = Child.objects.filter(
            caseload_assignments__staff=user,
            caseload_assignments__unassigned_at__isnull=True,
            overall_status='active',
            caseload_status='caseload'
        ).distinct()
        
        serializer = ChildListSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def non_caseload(self, request):
        """Get all non-caseload children."""
        children = self.queryset.filter(
            overall_status='active',
            caseload_status='non_caseload'
        )
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
    
    def perform_create(self, serializer):
        """
        When creating a new primary assignment, automatically unassign 
        the existing primary assignment for that child.
        """
        if serializer.validated_data.get('is_primary'):
            child = serializer.validated_data.get('child')
            # Unassign existing primary
            CaseloadAssignment.objects.filter(
                child=child,
                is_primary=True,
                unassigned_at__isnull=True
            ).update(unassigned_at=timezone.now())
        
        serializer.save(assigned_by=self.request.user)
    
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


class CaseNoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CaseNote model.
    Notes are scoped to a specific child via the child_pk URL kwarg.
    Staff can create notes and edit their own notes.
    Supervisors and admins can edit all notes and soft-delete.
    """

    serializer_class = CaseNoteSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        qs = CaseNote.objects.filter(
            is_deleted=False
        ).select_related('author', 'updated_by', 'child')
        if child_pk:
            qs = qs.filter(child_id=child_pk)
        # Apply search
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(author__first_name__icontains=q) |
                Q(author__last_name__icontains=q)
            )
        return qs

    def get_permissions(self):
        return [IsStaffMember()]

    def perform_create(self, serializer):
        child_pk = self.kwargs.get('child_pk')
        child = Child.objects.get(pk=child_pk)
        serializer.save(author=self.request.user, child=child)

    def update(self, request, *args, **kwargs):
        note = self.get_object()
        user = request.user
        is_supervisor_or_admin = user.is_superuser or (
            hasattr(user, 'role') and user.role in ['supervisor', 'admin']
        )
        if not is_supervisor_or_admin and note.author != user:
            return Response(
                {'detail': 'You can only edit your own notes.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Soft-delete a note. Only supervisors and admins can delete."""
        user = request.user
        is_supervisor_or_admin = user.is_superuser or (
            hasattr(user, 'role') and user.role in ['supervisor', 'admin']
        )
        if not is_supervisor_or_admin:
            return Response(
                {'detail': 'Only supervisors and admins can delete notes.'},
                status=status.HTTP_403_FORBIDDEN
            )
        note = self.get_object()
        note.is_deleted = True
        note.deleted_by = user
        note.deleted_at = timezone.now()
        note.save(update_fields=['is_deleted', 'deleted_by', 'deleted_at'])
        # Write audit log entry
        from audit.models import AuditLog
        AuditLog.objects.create(
            user=user,
            entity_type='CaseNote',
            entity_id=note.pk,
            action='deleted',
            old_value=f'Case note for {note.child.full_name} by {note.author.get_full_name()} deleted by {user.get_full_name()}',
            metadata={
                'child_id': note.child.pk,
                'child_name': note.child.full_name,
                'author_id': note.author.pk,
            }
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
