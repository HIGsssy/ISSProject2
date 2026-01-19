"""
Django views for core app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Child, Visit, Centre, VisitType, CaseloadAssignment


@login_required
def dashboard(request):
    """Main dashboard view."""
    user = request.user
    
    # Get user's primary caseload
    primary_caseload = Child.objects.filter(
        caseload_assignments__staff=user,
        caseload_assignments__is_primary=True,
        caseload_assignments__unassigned_at__isnull=True
    ).distinct()
    
    # Get recent visits
    recent_visits = Visit.objects.filter(
        staff=user
    ).select_related('child', 'centre', 'visit_type').order_by('-visit_date', '-start_time')[:10]
    
    context = {
        'primary_caseload_count': primary_caseload.count(),
        'recent_visits': recent_visits,
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def my_caseload(request):
    """My Caseload view showing staff's assigned children."""
    user = request.user
    
    # Get children from primary caseload assignments
    primary_caseload = Child.objects.filter(
        caseload_assignments__staff=user,
        caseload_assignments__is_primary=True,
        caseload_assignments__unassigned_at__isnull=True
    ).select_related('centre').prefetch_related('caseload_assignments__staff').distinct()
    
    # Get unique children from user's visits
    visited_children = Child.objects.filter(
        visits__staff=user
    ).select_related('centre').distinct()
    
    # Combine
    children = (primary_caseload | visited_children).filter(
        Q(status__in=['active', 'on_hold', 'non_caseload']) |
        Q(caseload_assignments__staff=user, caseload_assignments__unassigned_at__isnull=True)
    ).distinct()
    
    context = {
        'children': children,
        'view_type': 'my_caseload',
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
