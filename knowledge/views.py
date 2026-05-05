from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from caseworker.permissions import IsAdminOrReadOnly

from .models import (
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeEmbedding,
    KnowledgeSource,
)
from .serializers import (
    KnowledgeChunkSerializer,
    KnowledgeCollectionSerializer,
    KnowledgeEmbeddingSerializer,
    KnowledgeSourceSerializer,
)


class KnowledgeCollectionViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeCollection.objects.all()
    serializer_class = KnowledgeCollectionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]


class KnowledgeSourceViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeSource.objects.select_related(
        "collection", "owner", "case", "document_source"
    ).prefetch_related("allowed_users", "allowed_groups")
    serializer_class = KnowledgeSourceSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]


class KnowledgeChunkViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeChunk.objects.select_related("source", "source__collection")
    serializer_class = KnowledgeChunkSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]


class KnowledgeEmbeddingViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeEmbedding.objects.select_related(
        "chunk", "chunk__source", "chunk__source__collection"
    )
    serializer_class = KnowledgeEmbeddingSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
