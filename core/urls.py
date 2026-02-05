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
    path('children/import/', views.import_children, name='import_children'),
    path('children/import/preview/', views.import_children_preview, name='import_children_preview'),
    path('children/import/template/', views.download_children_template, name='download_children_template'),
    path('centres/', views.centre_list, name='centre_list'),
    path('centres/import/', views.import_centres, name='import_centres'),
    path('centres/import/preview/', views.import_centres_preview, name='import_centres_preview'),
    path('centres/import/template/', views.download_centres_template, name='download_centres_template'),
    path('children/non-caseload/', views.non_caseload_children, name='non_caseload_children'),
    path('children/<int:pk>/', views.child_detail, name='child_detail'),
    path('children/<int:pk>/edit/', views.edit_child, name='edit_child'),
    path('children/<int:pk>/manage-caseload/', views.manage_caseload, name='manage_caseload'),
    path('children/<int:pk>/discharge/', views.discharge_child, name='discharge_child'),
    path('visits/add/', views.add_visit, name='add_visit'),
    path('visits/add-site/', views.add_site_visit, name='add_site_visit'),
    path('visits/', views.staff_visits, name='staff_visits'),
    path('visits/<int:pk>/', views.visit_detail, name='visit_detail'),
    path('visits/<int:pk>/edit/', views.edit_visit, name='edit_visit'),
    path('community-partners/', views.community_partners, name='community_partners'),
    path('community-partners/add/', views.add_community_partner, name='add_community_partner'),
    path('community-partners/<int:pk>/edit/', views.edit_community_partner, name='edit_community_partner'),
    
    # Referrals temporarily disabled
    # path('referrals/', views.referrals_management, name='referrals_management'),
    # path('referrals/add/<int:child_pk>/', views.add_referral, name='add_referral'),
    # path('referrals/<int:pk>/edit/', views.edit_referral, name='edit_referral'),
]
