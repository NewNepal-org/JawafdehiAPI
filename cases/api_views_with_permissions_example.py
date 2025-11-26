"""
Example API views with permission integration
This file demonstrates how to use the permission system with DRF ViewSets
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Allegation, DocumentSource, Modification, Response
from .serializers import (
    AllegationSerializer, DocumentSourceSerializer,
    ModificationSerializer, ResponseSerializer
)
from .permissions import (
    AllegationPermission,
    DocumentSourcePermission,
    ResponsePermission,
    CanPublishCase,
    CanAssignContributors,
)
from .rules.utils import filter_cases_by_permission


class AllegationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Allegation with full permission support
    
    - Admins and Moderators can see all cases
    - Contributors can only see assigned cases
    - All roles can create cases
    - Only assigned users can edit cases
    - Only Moderators/Admins can delete cases
    """
    queryset = Allegation.objects.all()
    serializer_class = AllegationSerializer
    permission_classes = [IsAuthenticated, AllegationPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['allegation_type', 'state']
    search_fields = ['title', 'description', 'key_allegations']
    ordering_fields = ['created_at', 'updated_at']
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return filter_cases_by_permission(self.request.user, self.queryset)
    
    def perform_create(self, serializer):
        """Set initial state to draft when creating"""
        serializer.save(state='draft')
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanPublishCase])
    def publish(self, request, pk=None):
        """
        Publish a case (Moderators and Admins only)
        Changes state from 'in_review' to 'published'
        """
        allegation = self.get_object()
        
        if allegation.state != 'in_review':
            return DRFResponse(
                {'error': 'Case must be in review status to publish'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        allegation.state = 'published'
        allegation.save()
        
        # Log the modification
        Modification.objects.create(
            allegation=allegation,
            action='approved',
            user=request.user,
            notes='Case published'
        )
        
        return DRFResponse({'status': 'Case published successfully'})
    
    @action(detail=True, methods=['post'])
    def submit_for_review(self, request, pk=None):
        """
        Submit case for review (Contributors, Moderators, Admins)
        Changes state from 'draft' to 'in_review'
        """
        allegation = self.get_object()
        
        if allegation.state != 'draft':
            return DRFResponse(
                {'error': 'Only draft cases can be submitted for review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        allegation.state = 'in_review'
        allegation.save()
        
        # Log the modification
        Modification.objects.create(
            allegation=allegation,
            action='submitted',
            user=request.user,
            notes='Case submitted for review'
        )
        
        return DRFResponse({'status': 'Case submitted for review'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanAssignContributors])
    def assign_contributors(self, request, pk=None):
        """
        Assign contributors to a case (Moderators and Admins only)
        Expects: {"user_ids": [1, 2, 3]}
        """
        allegation = self.get_object()
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return DRFResponse(
                {'error': 'user_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.contrib.auth.models import User
        users = User.objects.filter(id__in=user_ids)
        allegation.contributors.set(users)
        
        return DRFResponse({
            'status': 'Contributors assigned successfully',
            'contributors': [u.username for u in users]
        })


class DocumentSourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DocumentSource with permission support
    
    - Users can only access documents for cases they have access to
    - All roles can create documents
    - Only assigned users or Moderators/Admins can edit/delete
    """
    queryset = DocumentSource.objects.all()
    serializer_class = DocumentSourceSerializer
    permission_classes = [IsAuthenticated, DocumentSourcePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['source_type', 'case']
    search_fields = ['title', 'description']
    
    def get_queryset(self):
        """Filter documents based on case access"""
        user = self.request.user
        
        # Admins and moderators see all documents
        if user.groups.filter(name__in=['Admin', 'Moderator']).exists():
            return self.queryset
        
        # Contributors see documents for their assigned cases
        return self.queryset.filter(case__contributors=user)


class ModificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Modification (audit log)
    Read-only, filtered by case access
    """
    queryset = Modification.objects.all()
    serializer_class = ModificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['allegation', 'action']
    
    def get_queryset(self):
        """Filter modifications based on case access"""
        user = self.request.user
        
        # Admins and moderators see all modifications
        if user.groups.filter(name__in=['Admin', 'Moderator']).exists():
            return self.queryset
        
        # Contributors see modifications for their assigned cases
        return self.queryset.filter(allegation__contributors=user)


class ResponseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Response with permission support
    
    - Users can only access responses for cases they have access to
    - Only Moderators/Admins can verify responses
    """
    queryset = Response.objects.all()
    serializer_class = ResponseSerializer
    permission_classes = [IsAuthenticated, ResponsePermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['allegation']
    
    def get_queryset(self):
        """Filter responses based on case access"""
        user = self.request.user
        
        # Admins and moderators see all responses
        if user.groups.filter(name__in=['Admin', 'Moderator']).exists():
            return self.queryset
        
        # Contributors see responses for their assigned cases
        return self.queryset.filter(allegation__contributors=user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanPublishCase])
    def verify(self, request, pk=None):
        """
        Verify a response (Moderators and Admins only)
        """
        response = self.get_object()
        
        if response.verified_at:
            return DRFResponse(
                {'error': 'Response is already verified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        response.verified_at = timezone.now()
        response.verified_by = request.user
        response.save()
        
        return DRFResponse({'status': 'Response verified successfully'})
