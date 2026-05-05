from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    KnowledgeChunkViewSet,
    KnowledgeCollectionViewSet,
    KnowledgeEmbeddingViewSet,
    KnowledgeSourceViewSet,
)

router = DefaultRouter()
router.register("collections", KnowledgeCollectionViewSet)
router.register("sources", KnowledgeSourceViewSet)
router.register("chunks", KnowledgeChunkViewSet)
router.register("embeddings", KnowledgeEmbeddingViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
