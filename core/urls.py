"""
URL configuration for core app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('my-caseload/', views.my_caseload, name='my_caseload'),
    path('children/', views.all_children, name='all_children'),
    path('children/non-caseload/', views.non_caseload_children, name='non_caseload_children'),
    path('children/<int:pk>/', views.child_detail, name='child_detail'),
    path('visits/add/', views.add_visit, name='add_visit'),
    path('visits/<int:pk>/edit/', views.edit_visit, name='edit_visit'),
]
