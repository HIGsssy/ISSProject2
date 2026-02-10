"""
URL configuration for reports app.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard, name='dashboard'),
    path('visits/', views.visits_report, name='visits'),
    path('staff-summary/', views.staff_summary_report, name='staff_summary'),
    path('caseload/', views.caseload_report, name='caseload'),
    path('children-served/', views.children_served_report, name='children_served'),
    path('age-out/', views.age_out_report, name='age_out'),
    path('age-progressions/', views.age_progression_report, name='age_progression'),
    path('month-added/', views.month_added_report, name='month_added'),
    path('staff-site-visits/', views.staff_site_visits_report, name='staff_site_visits'),
    path('site-visit-summary/', views.site_visit_summary_report, name='site_visit_summary'),
]
