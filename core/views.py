"""
Django views for core app.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.core.paginator import Paginator
from .models import Child, Visit, Centre, VisitType, CaseloadAssignment, CommunityPartner, Referral
from accounts.models import User
from .utils.csv_import import ChildCSVImporter, CentreCSVImporter, CSVImportError


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
        active_children_count = Child.objects.filter(overall_status='active').count()
        
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
        'overall_status': 'active',
        'caseload_status': 'caseload'
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
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    children = Child.objects.select_related('centre').prefetch_related('caseload_assignments__staff')
    
    # Apply database-level filters
    overall_status_filter = request.GET.get('overall_status', 'active')
    if overall_status_filter != 'all':
        children = children.filter(overall_status=overall_status_filter)
    
    caseload_status_filter = request.GET.get('caseload_status', 'all')
    if caseload_status_filter != 'all':
        children = children.filter(caseload_status=caseload_status_filter)
    
    on_hold_filter = request.GET.get('on_hold', 'all')
    if on_hold_filter == 'yes':
        children = children.filter(on_hold=True)
    elif on_hold_filter == 'no':
        children = children.filter(on_hold=False)
    
    # Fetch all matching children and prepare for search filtering
    all_children = list(children)
    total_before_search = len(all_children)
    
    # Apply search filter on encrypted fields (application-level)
    search = request.GET.get('search', '').strip()
    filtered_children = all_children
    search_applied = False
    
    if search:
        # Enforce minimum 3 characters
        if len(search) >= 3:
            search_lower = search.lower()
            filtered_children = [
                child for child in all_children
                if search_lower in child.first_name.lower() or search_lower in child.last_name.lower()
            ]
            search_applied = True
        else:
            # Search too short - show validation message but don't filter
            search = None
            filtered_children = all_children
    
    # Paginate the filtered results (50 per page)
    paginator = Paginator(filtered_children, 50)
    page_num = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
    
    context = {
        'page_obj': page_obj,
        'children': page_obj.object_list,
        'total_children': total_before_search,
        'total_matches': len(filtered_children),
        'overall_status_filter': overall_status_filter,
        'caseload_status_filter': caseload_status_filter,
        'on_hold_filter': on_hold_filter,
        'search': search,
        'search_applied': search_applied,
        'view_type': 'all',
    }
    
    return render(request, 'core/all_children.html', context)


@login_required
def non_caseload_children(request):
    """View all non-caseload children."""
    children = Child.objects.filter(
        overall_status='active',
        caseload_status='non_caseload'
    ).select_related('centre')
    
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
    
    # Get referrals with optional filtering
    referrals = child.referrals.select_related('community_partner', 'referred_by', 'status_updated_by')
    
    referral_status_filter = request.GET.get('referral_status', 'active')
    if referral_status_filter == 'active':
        # Active means pending or accepted
        referrals = referrals.filter(status__in=['pending', 'accepted'])
    elif referral_status_filter == 'completed':
        referrals = referrals.filter(status='completed')
    elif referral_status_filter == 'closed':
        # Closed means declined or cancelled
        referrals = referrals.filter(status__in=['declined', 'cancelled'])
    # else: all
    
    referrals = referrals.order_by('-referral_date')
    
    # Check if current user can discharge this child
    staff_can_discharge = child.can_be_discharged_by(request.user)
    
    context = {
        'child': child,
        'caseload_assignments': caseload_assignments,
        'visits': visits,
        'referrals': referrals,
        'referral_status_filter': referral_status_filter,
        'staff_can_discharge': staff_can_discharge,
    }
    
    return render(request, 'core/child_detail.html', context)


@login_required
def add_visit(request):
    """Add child visit form."""
    if request.method == 'POST':
        # Handle form submission (this will be handled by API in practice)
        return redirect('dashboard')
    
    # Get form data
    # Filter children based on user role
    user = request.user
    is_supervisor_or_admin = user.is_superuser or (hasattr(user, 'role') and user.role in ['supervisor', 'admin'])
    
    if is_supervisor_or_admin:
        # Supervisors and admins can see all active children
        children = Child.objects.filter(
            overall_status='active'
        ).order_by('last_name', 'first_name')
    else:
        # Staff can only see children in their caseload
        children = Child.objects.filter(
            caseload_assignments__staff=user,
            caseload_assignments__unassigned_at__isnull=True,
            overall_status='active',
            caseload_status='caseload'
        ).distinct().order_by('last_name', 'first_name')
    
    centres = Centre.objects.filter(status='active').order_by('name')
    visit_types = VisitType.objects.filter(is_active=True).order_by('name')
    
    # Pre-select child if provided in URL
    child_id = request.GET.get('child_id')
    selected_child = None
    selected_centre = None
    if child_id:
        selected_child = Child.objects.filter(pk=child_id).first()
        if selected_child and selected_child.centre:
            selected_centre = selected_child.centre
    
    context = {
        'children': children,
        'centres': centres,
        'visit_types': visit_types,
        'selected_child': selected_child,
        'selected_centre': selected_centre,
    }
    
    return render(request, 'core/add_visit.html', context)


@login_required
def add_site_visit(request):
    """Add site visit form."""
    if request.method == 'POST':
        # Handle form submission (this will be handled by API in practice)
        return redirect('dashboard')
    
    centres = Centre.objects.filter(status='active').order_by('name')
    visit_types = VisitType.objects.filter(is_active=True).order_by('name')
    
    context = {
        'centres': centres,
        'visit_types': visit_types,
    }
    
    return render(request, 'core/add_site_visit.html', context)


@login_required
def staff_visits(request):
    """View all visits for the current staff member."""
    user = request.user
    
    # Get all visits for this staff member, ordered by most recent first
    visits = Visit.objects.filter(
        staff=user
    ).select_related('child', 'centre', 'visit_type').order_by('-visit_date', '-created_at')
    
    # Apply pagination
    paginator = Paginator(visits, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'visits': page_obj.object_list,
        'total_visits_count': visits.count(),
    }
    
    return render(request, 'core/staff_visits.html', context)


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
        overall_status='active'
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
    """Add a new child - Multi-step intake form (Supervisors and Admins only)."""
    user = request.user
    
    # Check permissions - only supervisors and admins can add children
    if not (user.is_superuser or (hasattr(user, 'role') and user.role in ['supervisor', 'admin'])):
        return redirect('dashboard')
    
    if request.method == 'POST':
        # This will be handled by the frontend/API
        return redirect('all_children')
    
    # Get staff members for assignment
    staff_members = User.objects.filter(role='staff').order_by('last_name', 'first_name')
    centres = Centre.objects.filter(status='active').order_by('name')
    earlyon_centres = centres.filter(name__icontains='early')  # Filter centres with "early" in name
    
    context = {
        'centres': centres,
        'earlyon_centres': earlyon_centres,
        'staff_members': staff_members,
    }
    
    return render(request, 'core/add_child.html', context)


@login_required
def edit_child(request, pk):
    """Edit child information."""
    child = get_object_or_404(Child, pk=pk)
    
    # All authenticated staff/supervisors/admins can edit
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role in ['staff', 'supervisor', 'admin'])):
        messages.error(request, "You don't have permission to edit child records.")
        return redirect('child_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Update child information
            child.first_name = request.POST.get('first_name', '').strip()
            child.last_name = request.POST.get('last_name', '').strip()
            child.date_of_birth = request.POST.get('date_of_birth')
            
            # Address fields
            child.address_line1 = request.POST.get('address_line1', '').strip()
            child.address_line2 = request.POST.get('address_line2', '').strip()
            child.city = request.POST.get('city', '').strip()
            child.province = request.POST.get('province', 'ON').strip()
            child.postal_code = request.POST.get('postal_code', '').strip()
            
            # Guardian information
            child.guardian1_name = request.POST.get('guardian1_name', '').strip()
            child.guardian1_home_phone = request.POST.get('guardian1_home_phone', '').strip()
            child.guardian1_work_phone = request.POST.get('guardian1_work_phone', '').strip()
            child.guardian1_cell_phone = request.POST.get('guardian1_cell_phone', '').strip()
            child.guardian1_email = request.POST.get('guardian1_email', '').strip()
            child.guardian2_name = request.POST.get('guardian2_name', '').strip()
            child.guardian2_home_phone = request.POST.get('guardian2_home_phone', '').strip()
            child.guardian2_work_phone = request.POST.get('guardian2_work_phone', '').strip()
            child.guardian2_cell_phone = request.POST.get('guardian2_cell_phone', '').strip()
            child.guardian2_email = request.POST.get('guardian2_email', '').strip()
            
            # Centre
            centre_id = request.POST.get('centre')
            if centre_id:
                child.centre_id = centre_id
            else:
                child.centre = None
            
            # Caseload status (only for supervisors/admins)
            is_supervisor_or_admin = request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role in ['supervisor', 'admin'])
            if is_supervisor_or_admin:
                new_caseload_status = request.POST.get('caseload_status')
                if new_caseload_status and child.overall_status == 'active':
                    child.caseload_status = new_caseload_status
            
            # On hold status
            child.on_hold = request.POST.get('on_hold') == 'on'
            
            # Notes
            child.notes = request.POST.get('notes', '').strip()
            
            # Update metadata
            child.updated_by = request.user
            child.save()
            
            messages.success(request, f'{child.full_name} has been updated successfully.')
            return redirect('child_detail', pk=child.pk)
            
        except Exception as e:
            messages.error(request, f'Error updating child: {str(e)}')
    
    # Get centres for dropdown
    centres = Centre.objects.filter(status='active').order_by('name')
    
    # Check if user is supervisor/admin
    is_supervisor_or_admin = request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role in ['supervisor', 'admin'])
    
    context = {
        'child': child,
        'centres': centres,
        'is_supervisor_or_admin': is_supervisor_or_admin,
        'caseload_status_choices': Child.CASELOAD_STATUS_CHOICES,
    }
    
    return render(request, 'core/edit_child.html', context)


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


@login_required
def discharge_child(request, pk):
    """Discharge a child from services."""
    child = get_object_or_404(Child, pk=pk)
    
    # Check permissions using helper method
    if not child.can_be_discharged_by(request.user):
        raise PermissionDenied("You don't have permission to discharge this child.")
    
    # Prevent discharging already discharged children
    if child.overall_status == 'discharged':
        messages.warning(request, f'{child.full_name} is already discharged.')
        return redirect('child_detail', pk=child.pk)
    
    if request.method == 'POST':
        discharge_reason = request.POST.get('discharge_reason', '').strip()
        discharge_date = request.POST.get('discharge_date')
        
        if not discharge_reason:
            messages.error(request, 'Discharge reason is required.')
        elif not discharge_date:
            messages.error(request, 'Discharge date is required.')
        else:
            try:
                # Update child status and info
                child.overall_status = 'discharged'
                child.caseload_status = 'non_caseload'
                child.on_hold = False
                child.discharge_reason = discharge_reason
                child.end_date = discharge_date
                child.updated_by = request.user
                child.save()
                
                # Unassign all active caseload assignments
                CaseloadAssignment.objects.filter(
                    child=child,
                    unassigned_at__isnull=True
                ).update(
                    unassigned_at=timezone.now()
                )
                
                messages.success(request, f'{child.full_name} has been discharged successfully.')
                return redirect('child_detail', pk=child.pk)
            except Exception as e:
                messages.error(request, f'Error discharging child: {str(e)}')
    
    # Get active caseload assignments
    active_assignments = CaseloadAssignment.objects.filter(
        child=child,
        unassigned_at__isnull=True
    ).select_related('staff')
    
    context = {
        'child': child,
        'active_assignments': active_assignments,
    }
    
    return render(request, 'core/discharge_child.html', context)


# Community Partners Views
@login_required
def community_partners(request):
    """List all community partners."""
    # Filter by status if provided
    status_filter = request.GET.get('status', 'active')
    
    if status_filter == 'all':
        partners = CommunityPartner.objects.all()
    else:
        partners = CommunityPartner.objects.filter(status=status_filter)
    
    partners = partners.order_by('name')
    
    context = {
        'partners': partners,
        'status_filter': status_filter,
    }
    
    return render(request, 'core/community_partners.html', context)


@login_required
def add_community_partner(request):
    """Add a new community partner."""
    # Check permissions - staff, supervisors, and admins can add
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role in ['staff', 'supervisor', 'admin'])):
        messages.error(request, "You don't have permission to add community partners.")
        return redirect('community_partners')
    
    if request.method == 'POST':
        try:
            partner = CommunityPartner()
            partner.name = request.POST.get('name', '').strip()
            partner.partner_type = request.POST.get('partner_type', 'other')
            partner.contact_name = request.POST.get('contact_name', '').strip()
            partner.phone = request.POST.get('phone', '').strip()
            partner.email = request.POST.get('email', '').strip()
            partner.address_line1 = request.POST.get('address_line1', '').strip()
            partner.address_line2 = request.POST.get('address_line2', '').strip()
            partner.city = request.POST.get('city', '').strip()
            partner.province = request.POST.get('province', 'ON').strip()
            partner.postal_code = request.POST.get('postal_code', '').strip()
            partner.website = request.POST.get('website', '').strip()
            partner.notes = request.POST.get('notes', '').strip()
            partner.save()
            
            messages.success(request, f'{partner.name} has been added successfully.')
            return redirect('community_partners')
        except Exception as e:
            messages.error(request, f'Error adding community partner: {str(e)}')
    
    context = {
        'partner_types': CommunityPartner.PARTNER_TYPE_CHOICES,
    }
    
    return render(request, 'core/add_community_partner.html', context)


@login_required
def edit_community_partner(request, pk):
    """Edit community partner information."""
    partner = get_object_or_404(CommunityPartner, pk=pk)
    
    # Check permissions
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role in ['staff', 'supervisor', 'admin'])):
        messages.error(request, "You don't have permission to edit community partners.")
        return redirect('community_partners')
    
    if request.method == 'POST':
        try:
            partner.name = request.POST.get('name', '').strip()
            partner.partner_type = request.POST.get('partner_type', 'other')
            partner.contact_name = request.POST.get('contact_name', '').strip()
            partner.phone = request.POST.get('phone', '').strip()
            partner.email = request.POST.get('email', '').strip()
            partner.address_line1 = request.POST.get('address_line1', '').strip()
            partner.address_line2 = request.POST.get('address_line2', '').strip()
            partner.city = request.POST.get('city', '').strip()
            partner.province = request.POST.get('province', 'ON').strip()
            partner.postal_code = request.POST.get('postal_code', '').strip()
            partner.website = request.POST.get('website', '').strip()
            partner.status = request.POST.get('status', 'active')
            partner.notes = request.POST.get('notes', '').strip()
            partner.save()
            
            messages.success(request, f'{partner.name} has been updated successfully.')
            return redirect('community_partners')
        except Exception as e:
            messages.error(request, f'Error updating community partner: {str(e)}')
    
    context = {
        'partner': partner,
        'partner_types': CommunityPartner.PARTNER_TYPE_CHOICES,
        'status_choices': CommunityPartner.STATUS_CHOICES,
    }
    
    return render(request, 'core/edit_community_partner.html', context)


@login_required
def add_referral(request, child_pk):
    """Add a referral for a child."""
    child = get_object_or_404(Child, pk=child_pk)
    
    # Check permissions
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role in ['staff', 'supervisor', 'admin'])):
        messages.error(request, "You don't have permission to create referrals.")
        return redirect('child_detail', pk=child_pk)
    
    if request.method == 'POST':
        try:
            referral = Referral()
            referral.child = child
            referral.community_partner_id = request.POST.get('community_partner')
            referral.referred_by = request.user
            referral.referral_date = request.POST.get('referral_date')
            referral.reason = request.POST.get('reason', '').strip()
            referral.notes = request.POST.get('notes', '').strip()
            referral.save()
            
            messages.success(request, 'Referral created successfully.')
            return redirect('child_detail', pk=child_pk)
        except Exception as e:
            messages.error(request, f'Error creating referral: {str(e)}')
    
    # Get active community partners
    partners = CommunityPartner.objects.filter(status='active').order_by('name')
    
    context = {
        'child': child,
        'partners': partners,
    }
    
    return render(request, 'core/add_referral.html', context)


@login_required
def edit_referral(request, pk):
    """Edit referral and update status."""
    referral = get_object_or_404(
        Referral.objects.select_related('child', 'community_partner', 'referred_by', 'status_updated_by'),
        pk=pk
    )
    
    # Check permissions - staff, supervisors, and admins can edit
    if request.user.role not in ['staff', 'supervisor', 'admin']:
        messages.error(request, "You don't have permission to edit referrals.")
        return redirect('child_detail', pk=referral.child.pk)
    
    if request.method == 'POST':
        try:
            old_status = referral.status
            
            referral.community_partner_id = request.POST.get('community_partner')
            referral.referral_date = request.POST.get('referral_date')
            referral.status = request.POST.get('status')
            referral.reason = request.POST.get('reason', '').strip()
            referral.notes = request.POST.get('notes', '').strip()
            
            # Track status changes
            if old_status != referral.status:
                referral.status_updated_at = timezone.now()
                referral.status_updated_by = request.user
            
            referral.save()
            
            messages.success(request, 'Referral updated successfully.')
            return redirect('child_detail', pk=referral.child.pk)
        except Exception as e:
            messages.error(request, f'Error updating referral: {str(e)}')
    
    # Get active community partners
    partners = CommunityPartner.objects.filter(status='active').order_by('name')
    
    # Referral status choices
    status_choices = Referral.STATUS_CHOICES
    
    context = {
        'referral': referral,
        'child': referral.child,
        'partners': partners,
        'status_choices': status_choices,
    }
    return render(request, 'core/edit_referral.html', context)


@login_required
def referrals_management(request):
    """Referrals management page for supervisors and admins."""
    # Check permissions - supervisors and admins only
    if request.user.role not in ['supervisor', 'admin']:
        messages.error(request, "You don't have permission to access referrals management.")
        return redirect('dashboard')
    
    # Get all referrals with relationships
    referrals = Referral.objects.select_related(
        'child', 'community_partner', 'referred_by', 'status_updated_by'
    )
    
    # Status filtering
    status_filter = request.GET.get('status', 'active')
    if status_filter == 'active':
        referrals = referrals.filter(status__in=['pending', 'accepted'])
    elif status_filter == 'pending':
        referrals = referrals.filter(status='pending')
    elif status_filter == 'accepted':
        referrals = referrals.filter(status='accepted')
    elif status_filter == 'completed':
        referrals = referrals.filter(status='completed')
    elif status_filter == 'closed':
        referrals = referrals.filter(status__in=['declined', 'cancelled'])
    # else: all
    
    # Partner filtering
    partner_id = request.GET.get('partner')
    if partner_id:
        referrals = referrals.filter(community_partner_id=partner_id)
    
    # Staff filtering
    staff_id = request.GET.get('staff')
    if staff_id:
        referrals = referrals.filter(referred_by_id=staff_id)
    
    referrals = referrals.order_by('-referral_date')
    
    # Get unique partners and staff for filter dropdowns
    partners = CommunityPartner.objects.filter(status='active').order_by('name')
    staff_members = User.objects.filter(
        role__in=['staff', 'supervisor', 'admin'],
        is_active=True
    ).order_by('first_name', 'last_name')
    
    context = {
        'referrals': referrals,
        'status_filter': status_filter,
        'partner_id': partner_id,
        'staff_id': staff_id,
        'partners': partners,
        'staff_members': staff_members,
    }
    return render(request, 'core/referrals_management.html', context)


@login_required
def import_children(request):
    """Import children from CSV file."""
    # Check permissions - only supervisors and admins
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role in ['supervisor', 'admin'])):
        raise PermissionDenied("You don't have permission to import children.")
    
    if request.method == 'POST':
        # Handle file upload and import
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No file uploaded.')
            return redirect('import_children')
        
        csv_file = request.FILES['csv_file']
        
        # Validate file type
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Invalid file type. Please upload a CSV file.')
            return redirect('import_children')
        
        # Check file size (10MB limit)
        if csv_file.size > 10 * 1024 * 1024:
            messages.error(request, 'File too large. Maximum size is 10MB.')
            return redirect('import_children')
        
        try:
            importer = ChildCSVImporter(csv_file, request.user)
            result = importer.parse()
            
            # Store results in session for preview
            request.session['import_preview'] = {
                'valid': [
                    {
                        'row_num': row['row_num'],
                        'data': {k: str(v) if not isinstance(v, (str, int, type(None))) else v 
                                for k, v in row['data'].items() if k != 'centre'},
                        'centre_name': row['data'].get('centre').name if row['data'].get('centre') else ''
                    }
                    for row in result['valid']
                ],
                'invalid': [
                    {
                        'row_num': row['row_num'],
                        'data': row['raw_data'],
                        'errors': row['errors']
                    }
                    for row in result['invalid']
                ],
                'total': result['total']
            }
            
            # Check for duplicates
            duplicates = importer.check_duplicates()
            request.session['import_duplicates'] = [
                {
                    'row_num': dup['row_num'],
                    'name': dup['name'],
                    'dob': str(dup['dob']),
                    'existing_id': dup['existing_id']
                }
                for dup in duplicates
            ]
            
            return redirect('import_children_preview')
            
        except CSVImportError as e:
            messages.error(request, f'CSV Import Error: {str(e)}')
            return redirect('import_children')
        except Exception as e:
            messages.error(request, f'Unexpected error: {str(e)}')
            return redirect('import_children')
    
    # GET request - show upload form
    return render(request, 'core/import_children.html')


@login_required
def import_children_preview(request):
    """Preview CSV import before confirming."""
    # Check permissions - only supervisors and admins
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role in ['supervisor', 'admin'])):
        raise PermissionDenied("You don't have permission to import children.")
    
    # Get preview data from session
    preview_data = request.session.get('import_preview')
    duplicates = request.session.get('import_duplicates', [])
    
    if not preview_data:
        messages.error(request, 'No import preview available. Please upload a CSV file first.')
        return redirect('import_children')
    
    if request.method == 'POST':
        # Handle confirmed import
        skip_duplicates = request.POST.get('skip_duplicates') == 'on'
        
        # Need to re-parse the file stored in session
        # For simplicity, we'll reconstruct CSV from session data
        try:
            import io
            import csv
            
            # Reconstruct CSV content from valid rows
            output = io.StringIO()
            valid_rows = preview_data['valid']
            
            if valid_rows:
                # Write header
                headers = list(valid_rows[0]['data'].keys())
                if valid_rows[0].get('centre_name'):
                    headers.append('centre')
                
                writer = csv.DictWriter(output, fieldnames=headers)
                writer.writeheader()
                
                # Write data rows
                for row in valid_rows:
                    row_data = row['data'].copy()
                    if row.get('centre_name'):
                        row_data['centre'] = row['centre_name']
                    writer.writerow(row_data)
                
                # Create file-like object
                output.seek(0)
                from django.core.files.uploadedfile import SimpleUploadedFile
                csv_content = output.getvalue().encode('utf-8')
                csv_file = SimpleUploadedFile("import.csv", csv_content, content_type="text/csv")
                
                # Import records
                importer = ChildCSVImporter(csv_file, request.user)
                importer.parse()  # Re-parse to get proper objects
                result = importer.import_records(skip_duplicates=skip_duplicates)
                
                # Clear session data
                del request.session['import_preview']
                if 'import_duplicates' in request.session:
                    del request.session['import_duplicates']
                
                # Show results
                if result['created'] > 0:
                    messages.success(request, f"Successfully imported {result['created']} child record(s).")
                if result['skipped'] > 0:
                    messages.info(request, f"Skipped {result['skipped']} duplicate record(s).")
                if result['errors']:
                    messages.warning(request, f"{len(result['errors'])} record(s) failed to import.")
                
                return redirect('all_children')
                
        except Exception as e:
            messages.error(request, f'Import failed: {str(e)}')
            return redirect('import_children')
    
    # GET request - show preview
    context = {
        'preview': preview_data,
        'duplicates': duplicates,
        'has_duplicates': len(duplicates) > 0
    }
    
    return render(request, 'core/import_children_preview.html', context)


@login_required
def download_children_template(request):
    """Download CSV template for importing children."""
    # Generate template
    template_content = ChildCSVImporter.generate_template()
    
    # Create response
    response = HttpResponse(template_content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="children_import_template.csv"'
    
    return response


@login_required
def import_centres(request):
    """Import centres from CSV file."""
    # Check permissions - only superusers and admins
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin')):
        raise PermissionDenied("You don't have permission to import centres.")
    
    if request.method == 'POST':
        # Handle file upload and import
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No file uploaded.')
            return redirect('import_centres')
        
        csv_file = request.FILES['csv_file']
        
        # Validate file type
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Invalid file type. Please upload a CSV file.')
            return redirect('import_centres')
        
        # Check file size (10MB limit)
        if csv_file.size > 10 * 1024 * 1024:
            messages.error(request, 'File too large. Maximum size is 10MB.')
            return redirect('import_centres')
        
        try:
            importer = CentreCSVImporter(csv_file, request.user)
            result = importer.parse()
            
            # Store results in session for preview
            request.session['import_preview'] = {
                'valid': [
                    {
                        'row_num': row['row_num'],
                        'data': row['data']
                    }
                    for row in result['valid']
                ],
                'invalid': [
                    {
                        'row_num': row['row_num'],
                        'data': row['raw_data'],
                        'errors': row['errors']
                    }
                    for row in result['invalid']
                ],
                'total': result['total'],
                'import_type': 'centres'
            }
            
            return redirect('import_centres_preview')
            
        except CSVImportError as e:
            messages.error(request, f'CSV Import Error: {str(e)}')
            return redirect('import_centres')
        except Exception as e:
            messages.error(request, f'Unexpected error: {str(e)}')
            return redirect('import_centres')
    
    # GET request - show import form
    return render(request, 'core/import_centres.html', {
        'page_title': 'Import Centres',
    })


@login_required
def import_centres_preview(request):
    """Preview CSV import before confirming."""
    # Check permissions
    if not (request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin')):
        raise PermissionDenied("You don't have permission to import centres.")
    
    if request.method == 'POST':
        # Confirm import
        preview = request.session.get('import_preview', {})
        
        if not preview.get('valid'):
            messages.error(request, 'No valid rows to import.')
            return redirect('import_centres')
        
        try:
            importer = CentreCSVImporter(None, request.user)
            result = importer.import_rows(preview['valid'])
            
            messages.success(request, f"Successfully imported {result['created']} centres.")
            
            if result['errors']:
                for error in result['errors']:
                    messages.warning(request, f"Row {error['row_num']}: {error['error']}")
            
            # Clean up session
            if 'import_preview' in request.session:
                del request.session['import_preview']
            
            return redirect('centre_list')
            
        except Exception as e:
            messages.error(request, f'Import error: {str(e)}')
            return redirect('import_centres')
    
    # GET request - show preview
    preview = request.session.get('import_preview', {})
    
    if not preview:
        messages.error(request, 'No import preview available. Please upload a CSV file first.')
        return redirect('import_centres')
    
    return render(request, 'core/import_centres_preview.html', {
        'page_title': 'Import Centres Preview',
        'valid_rows': preview.get('valid', []),
        'invalid_rows': preview.get('invalid', []),
        'total_rows': preview.get('total', 0),
    })


@login_required
def download_centres_template(request):
    """Download CSV template for importing centres."""
    # Generate template
    template_content = CentreCSVImporter.get_import_template()
    
    # Create response
    response = HttpResponse(template_content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="centres_import_template.csv"'
    
    return response


@login_required
def centre_list(request):
    """List all centres."""
    centres = Centre.objects.all().order_by('name')
    
    context = {
        'page_title': 'Centres',
        'centres': centres,
    }
    
    return render(request, 'core/centre_list.html', context)
