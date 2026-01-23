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
]
