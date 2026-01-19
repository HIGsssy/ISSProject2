"""
URL configuration for core app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('my-caseload/', views.my_caseload, name='my_caseload'),
    path('children/', views.all_children, name='all_children'),
    path('children/add/', views.add_child, name='add_child'),
    path('children/non-caseload/', views.non_caseload_children, name='non_caseload_children'),
    path('children/<int:pk>/', views.child_detail, name='child_detail'),
    path('children/<int:pk>/edit/', views.edit_child, name='edit_child'),
    path('children/<int:pk>/manage-caseload/', views.manage_caseload, name='manage_caseload'),
    path('children/<int:pk>/discharge/', views.discharge_child, name='discharge_child'),
    path('visits/add/', views.add_visit, name='add_visit'),
    path('visits/<int:pk>/', views.visit_detail, name='visit_detail'),
    path('visits/<int:pk>/edit/', views.edit_visit, name='edit_visit'),
]
