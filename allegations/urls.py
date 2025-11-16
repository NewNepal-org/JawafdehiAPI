from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    AllegationViewSet, DocumentSourceViewSet, EvidenceViewSet,
    TimelineViewSet, ModificationViewSet, ResponseViewSet
)

router = DefaultRouter()
router.register(r'allegations', AllegationViewSet)
router.register(r'sources', DocumentSourceViewSet)
router.register(r'evidence', EvidenceViewSet)
router.register(r'timelines', TimelineViewSet)
router.register(r'modifications', ModificationViewSet)
router.register(r'responses', ResponseViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
