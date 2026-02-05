"""
Views for reports generation.
Accessible by staff, supervisors, admins, and auditors.
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
        return user.role in ['staff', 'supervisor', 'admin', 'auditor']
    return False


@login_required
@user_passes_test(can_access_reports)
def reports_dashboard(request):
    """Main reports dashboard."""
    user_is_staff = hasattr(request.user, 'role') and request.user.role == 'staff'
    
    context = {
        'page_title': 'Reports Dashboard',
        'user_is_staff': user_is_staff,
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
@user_passes_test(can_access_reports)
def visits_report(request):
    """Generate visits report with filtering options."""
    
    # Determine if current user is staff (not supervisor/admin/auditor)
    user_is_staff = hasattr(request.user, 'role') and request.user.role == 'staff'
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    child_id = request.GET.get('child')
    staff_id = request.GET.get('staff')
    centre_id = request.GET.get('centre')
    export_format = request.GET.get('export')
    
    # Force staff users to view only their own visits (ignore any staff parameter)
    if user_is_staff:
        staff_id = str(request.user.id)
    
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
    
    # Export to CSV if requested (not available for staff users)
    if export_format == 'csv' and not user_is_staff:
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
        },
        'user_is_staff': user_is_staff,
        'current_staff_name': request.user.get_full_name(),
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
    
    # Get all children grouped by overall_status
    children_by_overall_status = Child.objects.values('overall_status').annotate(
        count=Count('id')
    ).order_by('overall_status')
    
    # Get all children grouped by caseload_status
    children_by_caseload_status = Child.objects.values('caseload_status').annotate(
        count=Count('id')
    ).order_by('caseload_status')
    
    # Get caseload assignment statistics
    active_assignments = CaseloadAssignment.objects.filter(
        unassigned_at__isnull=True
    )
    
    primary_assignments = active_assignments.filter(is_primary=True).count()
    secondary_assignments = active_assignments.filter(is_primary=False).count()
    
    # Get children with visits but no caseload assignment
    children_with_visits_no_assignment = Child.objects.filter(
        overall_status='active',
        caseload_status='awaiting_assignment',
        visits__isnull=False
    ).distinct().count()
    
    context = {
        'children_by_overall_status': children_by_overall_status,
        'children_by_caseload_status': children_by_caseload_status,
        'primary_assignments': primary_assignments,
        'secondary_assignments': secondary_assignments,
        'children_with_visits_no_assignment': children_with_visits_no_assignment,
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


@login_required
@user_passes_test(can_access_reports)
def age_out_report(request):
    """Report for children 13+ years old (aging out)."""
    
    # Get filter parameters
    centre_id = request.GET.get('centre')
    export_format = request.GET.get('export')
    
    # Calculate date 13 years ago from today
    today = timezone.now().date()
    cutoff_date = today - relativedelta(years=13)
    
    # Get children who are 13+ (date_of_birth before cutoff)
    age_out_children = Child.objects.filter(
        date_of_birth__lte=cutoff_date,
        overall_status='active'  # Only active children
    ).select_related('centre')
    
    # Apply centre filter
    if centre_id:
        age_out_children = age_out_children.filter(centre_id=centre_id)
    
    # Calculate age for each child and when they turned 13
    children_data = []
    monthly_age_out = {}  # Track when each child turned 13
    
    for child in age_out_children:
        age_delta = relativedelta(today, child.date_of_birth)
        years = age_delta.years
        months = age_delta.months
        
        # Calculate when this child turned 13
        age_13_date = child.date_of_birth + relativedelta(years=13)
        age_13_month_key = age_13_date.strftime('%Y-%m')
        age_13_month_display = age_13_date.strftime('%B %Y')
        
        # Track monthly age outs
        if age_13_month_key not in monthly_age_out:
            monthly_age_out[age_13_month_key] = {
                'display': age_13_month_display,
                'count': 0,
                'date': age_13_date
            }
        monthly_age_out[age_13_month_key]['count'] += 1
        
        children_data.append({
            'child': child,
            'age_years': years,
            'age_months': months,
            'age_display': f"{years} years, {months} months",
            'aged_out_date': age_13_date,
            'aged_out_month': age_13_month_display
        })
    
    # Sort by age (oldest first)
    children_data.sort(key=lambda x: x['age_years'] * 12 + x['age_months'], reverse=True)
    
    # Sort monthly data by date (oldest first)
    monthly_age_out_list = sorted(monthly_age_out.values(), key=lambda x: x['date'])
    
    # Calculate bar widths for monthly data visualization
    if monthly_age_out_list:
        max_count = max(item['count'] for item in monthly_age_out_list)
        max_bar_width = 300  # Maximum bar width in pixels
        for item in monthly_age_out_list:
            # Calculate proportional bar width (20px per count, up to max_bar_width)
            item['bar_width'] = min((item['count'] * 20), max_bar_width) if max_count > 0 else 0
    
    # Centre breakdown
    centre_breakdown = {}
    for child_data in children_data:
        centre_name = child_data['child'].centre.name if child_data['child'].centre else 'Unassigned'
        if centre_name not in centre_breakdown:
            centre_breakdown[centre_name] = 0
        centre_breakdown[centre_name] += 1
    
    # Get filter options
    centres = Centre.objects.filter(status='active').order_by('name')
    
    # Export to CSV if requested
    if export_format == 'csv':
        return export_age_out_csv(children_data, centre_breakdown, monthly_age_out_list)
    
    context = {
        'children_data': children_data,
        'total_count': len(children_data),
        'centre_breakdown': sorted(centre_breakdown.items()),
        'monthly_age_out': monthly_age_out_list,
        'centres': centres,
        'selected_centre': centre_id,
    }
    
    return render(request, 'reports/age_out_report.html', context)


def export_age_out_csv(children_data, centre_breakdown, monthly_age_out_list):
    """Export age out report to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="age_out_report_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Age Out Report (Children 13+ Years)'])
    writer.writerow(['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow([])
    
    writer.writerow(['Summary'])
    writer.writerow(['Total Children 13+:', len(children_data)])
    writer.writerow([])
    
    writer.writerow(['Centre Breakdown'])
    writer.writerow(['Centre', 'Count'])
    for centre_name, count in sorted(centre_breakdown.items()):
        writer.writerow([centre_name, count])
    writer.writerow([])
    
    writer.writerow(['Monthly Age Out Breakdown'])
    writer.writerow(['Month', 'Children Aged Out'])
    for month_data in monthly_age_out_list:
        writer.writerow([month_data['display'], month_data['count']])
    writer.writerow([])
    
    writer.writerow(['Detailed List'])
    writer.writerow(['First Name', 'Last Name', 'Date of Birth', 'Age', 'Aged Out Month', 'Centre', 'Primary Staff'])
    for child_data in children_data:
        child = child_data['child']
        primary_staff = child.get_primary_staff()
        writer.writerow([
            child.first_name,
            child.last_name,
            child.date_of_birth,
            child_data['age_display'],
            child_data['aged_out_month'],
            child.centre.name if child.centre else 'Unassigned',
            primary_staff.get_full_name() if primary_staff else 'Unassigned'
        ])
    
    return response


@login_required
@user_passes_test(can_access_reports)
def month_added_report(request):
    """Report showing children added by month."""
    
    # Get filter parameters
    year = request.GET.get('year')
    centre_id = request.GET.get('centre')
    export_format = request.GET.get('export')
    
    # Default to current year
    if not year:
        year = timezone.now().year
    else:
        year = int(year)
    
    # Get all children with start_date
    children = Child.objects.exclude(start_date__isnull=True).select_related('centre')
    
    # Apply centre filter
    if centre_id:
        children = children.filter(centre_id=centre_id)
    
    # Group by month for the selected year
    monthly_data = []
    for month in range(1, 13):
        month_start = datetime(year, month, 1).date()
        if month == 12:
            month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        month_children = children.filter(
            start_date__gte=month_start,
            start_date__lte=month_end
        )
        
        monthly_data.append({
            'month': month_start.strftime('%B'),
            'month_num': month,
            'count': month_children.count(),
            'children': month_children.order_by('start_date')
        })
    
    # Calculate cumulative and total
    cumulative = 0
    for month_data in monthly_data:
        cumulative += month_data['count']
        month_data['cumulative'] = cumulative
    
    total_year = children.filter(
        start_date__year=year
    ).count()
    
    # Get filter options
    centres = Centre.objects.filter(status='active').order_by('name')
    current_year = timezone.now().year
    year_options = range(current_year, current_year - 6, -1)
    
    # Export to CSV if requested
    if export_format == 'csv':
        return export_month_added_csv(monthly_data, year, total_year)
    
    context = {
        'monthly_data': monthly_data,
        'total_year': total_year,
        'year': year,
        'centres': centres,
        'year_options': year_options,
        'selected_centre': centre_id,
    }
    
    return render(request, 'reports/month_added_report.html', context)


def export_month_added_csv(monthly_data, year, total_year):
    """Export month added report to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="month_added_report_{year}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Children Added by Month Report'])
    writer.writerow(['Year:', year])
    writer.writerow(['Total:', total_year])
    writer.writerow([])
    
    writer.writerow(['Month', 'New Children', 'Cumulative'])
    for month_data in monthly_data:
        writer.writerow([
            month_data['month'],
            month_data['count'],
            month_data['cumulative']
        ])
    
    return response


@login_required
@user_passes_test(can_access_reports)
def staff_site_visits_report(request):
    """Report showing site visits by staff member."""
    
    # Get filter parameters
    staff_id = request.GET.get('staff')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    export_format = request.GET.get('export')
    
    # Default date range (last 30 days)
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get site visits (visits where child is null)
    site_visits = Visit.objects.filter(
        child__isnull=True,
        visit_date__gte=start_date,
        visit_date__lte=end_date
    ).select_related('staff', 'centre', 'visit_type')
    
    # Apply staff filter
    if staff_id:
        site_visits = site_visits.filter(staff_id=staff_id)
    
    # Group by staff
    staff_summary = {}
    for visit in site_visits:
        staff_name = visit.staff.get_full_name()
        if staff_name not in staff_summary:
            staff_summary[staff_name] = {
                'staff': visit.staff,
                'total_visits': 0,
                'total_hours': 0,
                'centres_visited': set(),
                'visits': []
            }
        
        staff_summary[staff_name]['total_visits'] += 1
        duration = visit.calculate_duration() or 0
        staff_summary[staff_name]['total_hours'] += duration
        if visit.centre:
            staff_summary[staff_name]['centres_visited'].add(visit.centre.name)
        staff_summary[staff_name]['visits'].append(visit)
    
    # Convert sets to sorted lists and calculate averages
    for staff_name, data in staff_summary.items():
        data['centres_visited'] = sorted(list(data['centres_visited']))
        data['centres_count'] = len(data['centres_visited'])
        data['total_hours'] = round(data['total_hours'], 2)
        data['avg_hours_per_visit'] = round(data['total_hours'] / data['total_visits'], 2) if data['total_visits'] > 0 else 0
    
    # Sort by total hours
    staff_summary_list = sorted(staff_summary.values(), key=lambda x: x['total_hours'], reverse=True)
    
    # Get filter options
    staff_options = User.objects.filter(role__in=['staff', 'supervisor', 'admin']).order_by('last_name', 'first_name')
    
    # Export to CSV if requested
    if export_format == 'csv':
        return export_staff_site_visits_csv(staff_summary_list, start_date, end_date)
    
    context = {
        'staff_summary': staff_summary_list,
        'total_visits': site_visits.count(),
        'total_hours': round(sum([data['total_hours'] for data in staff_summary_list]), 2),
        'start_date': start_date,
        'end_date': end_date,
        'staff_options': staff_options,
        'selected_staff': staff_id,
    }
    
    return render(request, 'reports/staff_site_visits.html', context)


def export_staff_site_visits_csv(staff_summary_list, start_date, end_date):
    """Export staff site visits report to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="staff_site_visits_{start_date}_to_{end_date}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Staff Site Visits Report'])
    writer.writerow(['Period:', f"{start_date} to {end_date}"])
    writer.writerow([])
    
    writer.writerow(['Staff Name', 'Total Visits', 'Total Hours', 'Centres Visited', 'Avg Hours/Visit'])
    for data in staff_summary_list:
        writer.writerow([
            data['staff'].get_full_name(),
            data['total_visits'],
            data['total_hours'],
            ', '.join(data['centres_visited']),
            data['avg_hours_per_visit']
        ])
    
    return response


@login_required
@user_passes_test(can_access_reports)
def site_visit_summary_report(request):
    """Aggregate site visit summary report."""
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    centre_id = request.GET.get('centre')
    export_format = request.GET.get('export')
    
    # Default date range (last 30 days)
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get site visits
    site_visits = Visit.objects.filter(
        child__isnull=True,
        visit_date__gte=start_date,
        visit_date__lte=end_date
    ).select_related('staff', 'centre', 'visit_type')
    
    # Apply centre filter
    if centre_id:
        site_visits = site_visits.filter(centre_id=centre_id)
    
    # Calculate totals
    total_visits = site_visits.count()
    total_hours = sum([v.calculate_duration() or 0 for v in site_visits])
    
    # Group by centre
    centre_breakdown = {}
    for visit in site_visits:
        centre_name = visit.centre.name if visit.centre else 'Not Specified'
        if centre_name not in centre_breakdown:
            centre_breakdown[centre_name] = {
                'visits': 0,
                'hours': 0
            }
        centre_breakdown[centre_name]['visits'] += 1
        centre_breakdown[centre_name]['hours'] += visit.calculate_duration() or 0
    
    # Round hours and sort
    for centre_name, data in centre_breakdown.items():
        data['hours'] = round(data['hours'], 2)
    
    centre_breakdown_list = sorted(centre_breakdown.items(), key=lambda x: x[1]['visits'], reverse=True)
    
    # Group by visit type
    visit_type_breakdown = {}
    for visit in site_visits:
        type_name = visit.visit_type.name
        if type_name not in visit_type_breakdown:
            visit_type_breakdown[type_name] = 0
        visit_type_breakdown[type_name] += 1
    
    visit_type_breakdown_list = sorted(visit_type_breakdown.items(), key=lambda x: x[1], reverse=True)
    
    # Get filter options
    centres = Centre.objects.filter(status='active').order_by('name')
    
    # Export to CSV if requested
    if export_format == 'csv':
        return export_site_visit_summary_csv(
            total_visits, total_hours, centre_breakdown_list, 
            visit_type_breakdown_list, start_date, end_date
        )
    
    context = {
        'total_visits': total_visits,
        'total_hours': round(total_hours, 2),
        'centre_breakdown': centre_breakdown_list,
        'visit_type_breakdown': visit_type_breakdown_list,
        'start_date': start_date,
        'end_date': end_date,
        'centres': centres,
        'selected_centre': centre_id,
    }
    
    return render(request, 'reports/site_visit_summary.html', context)


def export_site_visit_summary_csv(total_visits, total_hours, centre_breakdown, visit_type_breakdown, start_date, end_date):
    """Export site visit summary report to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="site_visit_summary_{start_date}_to_{end_date}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Site Visit Summary Report'])
    writer.writerow(['Period:', f"{start_date} to {end_date}"])
    writer.writerow([])
    
    writer.writerow(['Overall Summary'])
    writer.writerow(['Total Site Visits:', total_visits])
    writer.writerow(['Total Hours:', round(total_hours, 2)])
    writer.writerow([])
    
    writer.writerow(['Centre Breakdown'])
    writer.writerow(['Centre', 'Visits', 'Hours'])
    for centre_name, data in centre_breakdown:
        writer.writerow([centre_name, data['visits'], data['hours']])
    writer.writerow([])
    
    writer.writerow(['Visit Type Breakdown'])
    writer.writerow(['Visit Type', 'Count'])
    for type_name, count in visit_type_breakdown:
        writer.writerow([type_name, count])
    
    return response
