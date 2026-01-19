"""
Views for reports generation.
Only accessible by supervisors, admins, and auditors.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
import csv

from core.models import Visit, Child, Centre, CaseloadAssignment
from accounts.models import User


def can_access_reports(user):
    """Check if user can access reports."""
    if user.is_superuser:
        return True
    if hasattr(user, 'role'):
        return user.role in ['supervisor', 'admin', 'auditor']
    return False


@login_required
@user_passes_test(can_access_reports)
def reports_dashboard(request):
    """Main reports dashboard."""
    context = {
        'page_title': 'Reports Dashboard',
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
@user_passes_test(can_access_reports)
def visits_report(request):
    """Generate visits report with filtering options."""
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    child_id = request.GET.get('child')
    staff_id = request.GET.get('staff')
    centre_id = request.GET.get('centre')
    export_format = request.GET.get('export')
    
    # Build queryset
    visits = Visit.objects.select_related('child', 'staff', 'centre', 'visit_type')
    
    # Apply filters
    if start_date:
        visits = visits.filter(visit_date__gte=start_date)
    if end_date:
        visits = visits.filter(visit_date__lte=end_date)
    if child_id:
        visits = visits.filter(child_id=child_id)
    if staff_id:
        visits = visits.filter(staff_id=staff_id)
    if centre_id:
        visits = visits.filter(centre_id=centre_id)
    
    # Calculate totals
    total_visits = visits.count()
    total_hours = sum([v.calculate_duration() or 0 for v in visits])
    flagged_count = visits.filter(flagged_for_review=True).count()
    
    # Export to CSV if requested
    if export_format == 'csv':
        return export_visits_csv(visits)
    
    # Get filter options
    children = Child.objects.all().order_by('last_name', 'first_name')
    staff = User.objects.filter(role__in=['staff', 'supervisor', 'admin']).order_by('last_name', 'first_name')
    centres = Centre.objects.filter(status='active').order_by('name')
    
    context = {
        'visits': visits[:100],  # Limit to first 100 for display
        'total_visits': total_visits,
        'total_hours': round(total_hours, 2),
        'flagged_count': flagged_count,
        'children': children,
        'staff': staff,
        'centres': centres,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'child_id': child_id,
            'staff_id': staff_id,
            'centre_id': centre_id,
        }
    }
    
    return render(request, 'reports/visits_report.html', context)


def export_visits_csv(visits):
    """Export visits to CSV format."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="visits_report_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Visit Date', 'Child Name', 'Staff Name', 'Centre', 'Visit Type',
        'Start Time', 'End Time', 'Duration (hours)', 'Location Description',
        'Flagged', 'Notes'
    ])
    
    for visit in visits:
        writer.writerow([
            visit.visit_date,
            visit.child.full_name,
            visit.staff.get_full_name(),
            visit.centre.name if visit.centre else '',
            visit.visit_type.name,
            visit.start_time,
            visit.end_time,
            visit.calculate_duration() or 0,
            visit.location_description,
            'Yes' if visit.flagged_for_review else 'No',
            visit.notes,
        ])
    
    return response


@login_required
@user_passes_test(can_access_reports)
def staff_summary_report(request):
    """Staff productivity summary report."""
    
    # Get date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        # Default to last 30 days
        start_date = (timezone.now() - timedelta(days=30)).date()
    if not end_date:
        end_date = timezone.now().date()
    
    # Get all staff users
    staff = User.objects.filter(role__in=['staff', 'supervisor', 'admin'])
    
    # Calculate stats for each staff member
    staff_stats = []
    for staff_member in staff:
        visits = Visit.objects.filter(
            staff=staff_member,
            visit_date__gte=start_date,
            visit_date__lte=end_date
        )
        
        total_visits = visits.count()
        total_hours = sum([v.calculate_duration() or 0 for v in visits])
        unique_children = visits.values('child').distinct().count()
        
        # Get current caseload count
        caseload_count = CaseloadAssignment.objects.filter(
            staff=staff_member,
            unassigned_at__isnull=True
        ).count()
        
        staff_stats.append({
            'staff': staff_member,
            'total_visits': total_visits,
            'total_hours': round(total_hours, 2),
            'unique_children': unique_children,
            'caseload_count': caseload_count,
        })
    
    # Sort by total hours descending
    staff_stats.sort(key=lambda x: x['total_hours'], reverse=True)
    
    context = {
        'staff_stats': staff_stats,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'reports/staff_summary.html', context)


@login_required
@user_passes_test(can_access_reports)
def caseload_report(request):
    """Caseload vs non-caseload children report."""
    
    # Get all children grouped by status
    children_by_status = Child.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Get caseload assignment statistics
    active_assignments = CaseloadAssignment.objects.filter(
        unassigned_at__isnull=True
    )
    
    primary_assignments = active_assignments.filter(is_primary=True).count()
    secondary_assignments = active_assignments.filter(is_primary=False).count()
    
    # Get children with visits but no caseload
    non_caseload_children_with_visits = Child.objects.filter(
        status='non_caseload',
        visits__isnull=False
    ).distinct().count()
    
    context = {
        'children_by_status': children_by_status,
        'primary_assignments': primary_assignments,
        'secondary_assignments': secondary_assignments,
        'non_caseload_with_visits': non_caseload_children_with_visits,
    }
    
    return render(request, 'reports/caseload_report.html', context)
