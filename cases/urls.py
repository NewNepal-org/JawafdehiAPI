"""
URL configuration for the cases app API.

See: .kiro/specs/accountability-platform-core/design.md
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    CaseViewSet,
    DocumentSourceViewSet,
    JawafEntityViewSet,
    StatisticsView,
    FeedbackView
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'cases', CaseViewSet, basename='case')
router.register(r'sources', DocumentSourceViewSet, basename='documentsource')
router.register(r'entities', JawafEntityViewSet, basename='jawafentity')

urlpatterns = [
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    path('feedback/', FeedbackView.as_view(), name='feedback'),
    path('', include(router.urls)),
]
