"""
Django views for core app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Child, Visit, Centre, VisitType, CaseloadAssignment
from accounts.models import User


@login_required
def dashboard(request):
    """Main dashboard view."""
    user = request.user
    
    # Check if user is supervisor or admin
    is_supervisor_or_admin = hasattr(user, 'role') and user.role in ['supervisor', 'admin']
    
    if is_supervisor_or_admin:
        # Supervisor/Admin Dashboard
        from datetime import timedelta
        from django.utils import timezone
        
        # Total active children
        active_children_count = Child.objects.filter(status='active').count()
        
        # Visits in last 30 days
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_visits_count = Visit.objects.filter(visit_date__gte=thirty_days_ago).count()
        
        # Staff caseload summary
        staff_members = User.objects.filter(role='staff').order_by('last_name', 'first_name')
        
        context = {
            'is_supervisor': True,
            'active_children_count': active_children_count,
            'recent_visits_count': recent_visits_count,
            'staff_members': staff_members,
        }
    else:
        # Staff Dashboard
        # Get user's primary caseload
        primary_caseload = CaseloadAssignment.objects.filter(
            staff=user,
            is_primary=True,
            unassigned_at__isnull=True
        ).select_related('child')
        
        # Get user's secondary caseload
        secondary_caseload = CaseloadAssignment.objects.filter(
            staff=user,
            is_primary=False,
            unassigned_at__isnull=True
        ).select_related('child')
        
        # Get recent visits
        recent_visits = Visit.objects.filter(
            staff=user
        ).select_related('child', 'centre', 'visit_type').order_by('-visit_date', '-start_time')[:10]
        
        context = {
            'is_supervisor': False,
            'primary_caseload_count': primary_caseload.count(),
            'secondary_caseload_count': secondary_caseload.count(),
            'recent_visits': recent_visits,
        }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def my_caseload(request):
    """My Caseload view showing staff's assigned children."""
    user = request.user
    
    # Only staff should see caseload - supervisors/admins should not have caseloads
    if hasattr(user, 'role') and user.role in ['supervisor', 'admin']:
        # Redirect supervisors/admins to all children view
        return redirect('all_children')
    
    # Get filter type (primary or secondary)
    assignment_type = request.GET.get('type', 'primary')
    
    # Base queryset for active assignments
    base_filter = {
        'caseload_assignments__staff': user,
        'caseload_assignments__unassigned_at__isnull': True,
        'status__in': ['active', 'on_hold']  # Exclude discharged and non-caseload
    }
    
    # Add primary/secondary filter
    if assignment_type == 'secondary':
        base_filter['caseload_assignments__is_primary'] = False
    else:
        base_filter['caseload_assignments__is_primary'] = True
    
    # Get children from caseload assignments
    children = Child.objects.filter(**base_filter).select_related(
        'centre'
    ).prefetch_related('caseload_assignments__staff').distinct()
    
    # Get counts for both types
    primary_count = CaseloadAssignment.objects.filter(
        staff=user,
        is_primary=True,
        unassigned_at__isnull=True
    ).count()
    
    secondary_count = CaseloadAssignment.objects.filter(
        staff=user,
        is_primary=False,
        unassigned_at__isnull=True
    ).count()
    
    context = {
        'children': children,
        'view_type': 'my_caseload',
        'assignment_type': assignment_type,
        'primary_count': primary_count,
        'secondary_count': secondary_count,
    }
    
    return render(request, 'core/my_caseload.html', context)


@login_required
def all_children(request):
    """View all children."""
    children = Child.objects.select_related('centre').prefetch_related('caseload_assignments__staff')
    
    # Apply status filter if provided
    status_filter = request.GET.get('status')
    if status_filter:
        children = children.filter(status=status_filter)
    
    # Apply search if provided
    search = request.GET.get('search')
    if search:
        children = children.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(guardian1_name__icontains=search)
        )
    
    context = {
        'children': children,
        'status_filter': status_filter,
        'search': search,
        'view_type': 'all',
    }
    
    return render(request, 'core/all_children.html', context)


@login_required
def non_caseload_children(request):
    """View all non-caseload children."""
    children = Child.objects.filter(status='non_caseload').select_related('centre')
    
    context = {
        'children': children,
        'view_type': 'non_caseload',
    }
    
    return render(request, 'core/non_caseload_children.html', context)


@login_required
def child_detail(request, pk):
    """Child detail view."""
    child = get_object_or_404(
        Child.objects.select_related('centre', 'created_by', 'updated_by'),
        pk=pk
    )
    
    # Get caseload assignments
    caseload_assignments = child.caseload_assignments.select_related('staff', 'assigned_by').order_by('-assigned_at')
    
    # Get recent visits
    visits = child.visits.select_related('staff', 'centre', 'visit_type').order_by('-visit_date', '-start_time')[:20]
    
    context = {
        'child': child,
        'caseload_assignments': caseload_assignments,
        'visits': visits,
    }
    
    return render(request, 'core/child_detail.html', context)


@login_required
def add_visit(request):
    """Add visit form."""
    if request.method == 'POST':
        # Handle form submission (this will be handled by API in practice)
        return redirect('dashboard')
    
    # Get form data
    children = Child.objects.filter(
        Q(status__in=['active', 'on_hold', 'non_caseload'])
    ).order_by('last_name', 'first_name')
    
    centres = Centre.objects.filter(status='active').order_by('name')
    visit_types = VisitType.objects.filter(is_active=True).order_by('name')
    
    # Pre-select child if provided in URL
    child_id = request.GET.get('child_id')
    selected_child = None
    if child_id:
        selected_child = Child.objects.filter(pk=child_id).first()
    
    context = {
        'children': children,
        'centres': centres,
        'visit_types': visit_types,
        'selected_child': selected_child,
    }
    
    return render(request, 'core/add_visit.html', context)


@login_required
@login_required
def visit_detail(request, pk):
    """Visit detail view - all users can view, only certain users can edit."""
    visit = get_object_or_404(Visit.objects.select_related(
        'child', 'staff', 'centre', 'visit_type'
    ), pk=pk)
    
    # Check if user can edit this visit
    user = request.user
    can_edit = False
    
    if user.is_superuser:
        can_edit = True
    elif hasattr(user, 'role'):
        if user.role in ['supervisor', 'admin']:
            can_edit = True
        elif user.role == 'staff' and visit.staff == user:
            can_edit = True
    
    context = {
        'visit': visit,
        'can_edit': can_edit,
    }
    
    return render(request, 'core/visit_detail.html', context)


@login_required
def edit_visit(request, pk):
    """Edit visit form."""
    visit = get_object_or_404(Visit, pk=pk)
    
    # Check permissions
    user = request.user
    can_edit = False
    
    if user.is_superuser:
        can_edit = True
    elif hasattr(user, 'role'):
        if user.role in ['supervisor', 'admin']:
            can_edit = True
        elif user.role == 'staff' and visit.staff == user:
            can_edit = True
    
    if not can_edit:
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Handle form submission (this will be handled by API in practice)
        return redirect('child_detail', pk=visit.child.pk)
    
    # Get form data
    children = Child.objects.filter(
        Q(status__in=['active', 'on_hold', 'non_caseload'])
    ).order_by('last_name', 'first_name')
    
    centres = Centre.objects.filter(status='active').order_by('name')
    visit_types = VisitType.objects.filter(is_active=True).order_by('name')
    
    context = {
        'visit': visit,
        'children': children,
        'centres': centres,
        'visit_types': visit_types,
    }
    
    return render(request, 'core/edit_visit.html', context)


@login_required
def add_child(request):
    """Add a new child."""
    user = request.user
    
    # Check permissions
    if not (user.is_superuser or (hasattr(user, 'role') and user.role in ['staff', 'supervisor', 'admin'])):
        return redirect('dashboard')
    
    if request.method == 'POST':
        # This will be handled by the frontend/API
        return redirect('all_children')
    
    # Get staff members for assignment (only for supervisors/admins)
    staff_members = None
    is_supervisor_or_admin = user.is_superuser or (hasattr(user, 'role') and user.role in ['supervisor', 'admin'])
    
    if is_supervisor_or_admin:
        staff_members = User.objects.filter(role='staff').order_by('last_name', 'first_name')
    
    centres = Centre.objects.filter(status='active').order_by('name')
    
    context = {
        'centres': centres,
        'staff_members': staff_members,
        'is_supervisor_or_admin': is_supervisor_or_admin,
    }
    
    return render(request, 'core/add_child.html', context)


@login_required
def manage_caseload(request, pk):
    """Manage caseload assignments for a child (supervisors/admins only)."""
    user = request.user
    
    # Check permissions
    if not (user.is_superuser or (hasattr(user, 'role') and user.role in ['supervisor', 'admin'])):
        return redirect('child_detail', pk=pk)
    
    child = get_object_or_404(Child, pk=pk)
    
    if request.method == 'POST':
        # This will be handled by the API
        return redirect('child_detail', pk=pk)
    
    # Get all staff members
    staff_members = User.objects.filter(role='staff').order_by('last_name', 'first_name')
    
    # Get current assignments
    current_assignments = CaseloadAssignment.objects.filter(
        child=child,
        unassigned_at__isnull=True
    ).select_related('staff')
    
    # Check if child already has a primary assignment
    has_primary = current_assignments.filter(is_primary=True).exists()
    
    context = {
        'child': child,
        'staff_members': staff_members,
        'current_assignments': current_assignments,
        'has_primary': has_primary,
    }
    
    return render(request, 'core/manage_caseload.html', context)
