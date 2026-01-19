"""
API URL configuration for core app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    CentreViewSet, ChildViewSet, VisitTypeViewSet,
    VisitViewSet, CaseloadAssignmentViewSet
)

router = DefaultRouter()
router.register(r'centres', CentreViewSet, basename='centre')
router.register(r'children', ChildViewSet, basename='child')
router.register(r'visit-types', VisitTypeViewSet, basename='visittype')
router.register(r'visits', VisitViewSet, basename='visit')
router.register(r'caseloads', CaseloadAssignmentViewSet, basename='caseload')

urlpatterns = [
    path('', include(router.urls)),
]
