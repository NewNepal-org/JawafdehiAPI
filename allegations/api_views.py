from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Allegation, DocumentSource, Evidence, Timeline, Modification, Response
from .serializers import (
    AllegationSerializer, DocumentSourceSerializer, EvidenceSerializer,
    TimelineSerializer, ModificationSerializer, ResponseSerializer
)


class AllegationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Allegation.objects.all()
    serializer_class = AllegationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['allegation_type', 'state', 'status']
    search_fields = ['title', 'description', 'key_allegations']
    ordering_fields = ['created_at', 'first_public_date']


class DocumentSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DocumentSource.objects.all()
    serializer_class = DocumentSourceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['source_type']
    search_fields = ['title', 'description']


class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Evidence.objects.all()
    serializer_class = EvidenceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['allegation']


class TimelineViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Timeline.objects.all()
    serializer_class = TimelineSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['allegation']


class ModificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Modification.objects.all()
    serializer_class = ModificationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['allegation', 'action']


class ResponseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Response.objects.all()
    serializer_class = ResponseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['allegation']
