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
from dateutil.relativedelta import relativedelta
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


def calculate_age_in_months(date_of_birth, reference_date=None):
    """Calculate age in months from date of birth."""
    if reference_date is None:
        reference_date = timezone.now().date()
    
    age_delta = relativedelta(reference_date, date_of_birth)
    return age_delta.years * 12 + age_delta.months


def get_age_group(age_in_months):
    """Determine age group based on age in months."""
    if age_in_months <= 18:
        return 'infant'
    elif age_in_months < 30:
        return 'toddler'
    elif age_in_months <= 45.6:  # 3.8 years
        return 'preschooler'
    elif age_in_months < 72:  # 6 years
        return 'jk_sk'
    elif age_in_months < 144:  # 12 years
        return 'school_age'
    else:
        return 'other'


@login_required
@user_passes_test(can_access_reports)
def children_served_report(request):
    """Children served metrics report with age breakdowns."""
    
    # Get filter parameters
    report_year = request.GET.get('year')
    report_month = request.GET.get('month')
    staff_id = request.GET.get('staff')
    centre_id = request.GET.get('centre')
    export_format = request.GET.get('export')
    
    # Default to current year if not specified
    if not report_year:
        report_year = timezone.now().year
    else:
        report_year = int(report_year)
    
    # Determine date range
    if report_month:
        report_month = int(report_month)
        start_date = datetime(report_year, report_month, 1).date()
        # Get last day of month
        if report_month == 12:
            end_date = datetime(report_year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(report_year, report_month + 1, 1).date() - timedelta(days=1)
        period_label = f"{start_date.strftime('%B %Y')}"
    else:
        start_date = datetime(report_year, 1, 1).date()
        end_date = datetime(report_year, 12, 31).date()
        period_label = str(report_year)
    
    # Build base queryset - children who had visits during the period
    children_with_visits = Child.objects.filter(
        visits__visit_date__gte=start_date,
        visits__visit_date__lte=end_date
    ).distinct()
    
    # Apply additional filters
    if staff_id:
        children_with_visits = children_with_visits.filter(
            visits__staff_id=staff_id,
            visits__visit_date__gte=start_date,
            visits__visit_date__lte=end_date
        ).distinct()
    
    if centre_id:
        children_with_visits = children_with_visits.filter(
            visits__centre_id=centre_id,
            visits__visit_date__gte=start_date,
            visits__visit_date__lte=end_date
        ).distinct()
    
    # Calculate metrics
    total_children = children_with_visits.count()
    
    # NEW children - those whose start_date is within the period
    new_children = children_with_visits.filter(
        start_date__gte=start_date,
        start_date__lte=end_date
    ).count()
    
    # Age group breakdowns - calculate age at end of period
    age_groups = {
        'infant': 0,
        'toddler': 0,
        'preschooler': 0,
        'jk_sk': 0,
        'school_age': 0,
        'other': 0,
    }
    
    for child in children_with_visits:
        age_in_months = calculate_age_in_months(child.date_of_birth, end_date)
        age_group = get_age_group(age_in_months)
        age_groups[age_group] += 1
    
    # Monthly breakdown if viewing annual report
    monthly_data = []
    if not report_month:
        for month in range(1, 13):
            month_start = datetime(report_year, month, 1).date()
            if month == 12:
                month_end = datetime(report_year + 1, 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(report_year, month + 1, 1).date() - timedelta(days=1)
            
            # Children with visits in this month
            month_children = Child.objects.filter(
                visits__visit_date__gte=month_start,
                visits__visit_date__lte=month_end
            ).distinct()
            
            # Apply same filters
            if staff_id:
                month_children = month_children.filter(
                    visits__staff_id=staff_id,
                    visits__visit_date__gte=month_start,
                    visits__visit_date__lte=month_end
                ).distinct()
            
            if centre_id:
                month_children = month_children.filter(
                    visits__centre_id=centre_id,
                    visits__visit_date__gte=month_start,
                    visits__visit_date__lte=month_end
                ).distinct()
            
            month_new = month_children.filter(
                start_date__gte=month_start,
                start_date__lte=month_end
            ).count()
            
            monthly_data.append({
                'month': month_start.strftime('%B'),
                'total': month_children.count(),
                'new': month_new,
            })
    
    # Get filter options
    staff = User.objects.filter(role__in=['staff', 'supervisor', 'admin']).order_by('last_name', 'first_name')
    centres = Centre.objects.filter(status='active').order_by('name')
    
    # Generate year options (current year and previous 5 years)
    current_year = timezone.now().year
    year_options = range(current_year, current_year - 6, -1)
    
    context = {
        'total_children': total_children,
        'new_children': new_children,
        'age_groups': age_groups,
        'monthly_data': monthly_data,
        'period_label': period_label,
        'staff': staff,
        'centres': centres,
        'year_options': year_options,
        'filters': {
            'year': report_year,
            'month': report_month,
            'staff_id': staff_id,
            'centre_id': centre_id,
        }
    }
    
    if export_format == 'csv':
        return export_children_served_csv(context)
    
    return render(request, 'reports/children_served.html', context)


def export_children_served_csv(data):
    """Export children served report to CSV format."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="children_served_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Children Served Report'])
    writer.writerow(['Period:', data['period_label']])
    writer.writerow([])
    
    writer.writerow(['Summary Metrics'])
    writer.writerow(['Total Children Served', data['total_children']])
    writer.writerow(['New Children', data['new_children']])
    writer.writerow([])
    
    writer.writerow(['Age Group Breakdown'])
    writer.writerow(['Infants (0-18 months)', data['age_groups']['infant']])
    writer.writerow(['Toddlers (>18-<30 months)', data['age_groups']['toddler']])
    writer.writerow(['Preschoolers (>30 months-3.8 years)', data['age_groups']['preschooler']])
    writer.writerow(['JK/SK (>3.8-<6 years)', data['age_groups']['jk_sk']])
    writer.writerow(['School Age (6-12 years)', data['age_groups']['school_age']])
    writer.writerow([])
    
    if data['monthly_data']:
        writer.writerow(['Monthly Breakdown'])
        writer.writerow(['Month', 'Total Children', 'New Children'])
        for month_data in data['monthly_data']:
            writer.writerow([month_data['month'], month_data['total'], month_data['new']])
    
    return response
