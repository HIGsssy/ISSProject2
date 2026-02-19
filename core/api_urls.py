"""
API URL configuration for core app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    CentreViewSet, ChildViewSet, VisitTypeViewSet,
    VisitViewSet, CaseloadAssignmentViewSet, CaseNoteViewSet
)

router = DefaultRouter()
router.register(r'centres', CentreViewSet, basename='centre')
router.register(r'children', ChildViewSet, basename='child')
router.register(r'visit-types', VisitTypeViewSet, basename='visittype')
router.register(r'visits', VisitViewSet, basename='visit')
router.register(r'caseloads', CaseloadAssignmentViewSet, basename='caseload')

urlpatterns = [
    path('', include(router.urls)),
    path('children/<int:child_pk>/case-notes/', CaseNoteViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='child-case-notes-list'),
    path('children/<int:child_pk>/case-notes/<int:pk>/', CaseNoteViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    }), name='child-case-notes-detail'),
]
