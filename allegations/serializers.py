from rest_framework import serializers
from .models import Allegation, AllegationEntity, Response, AuditLog


class AllegationEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AllegationEntity
        fields = ["id", "entity_id", "entity_type", "entity_name", "role"]


class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ["id", "entity_id", "content", "verification_method", "status", "created_at", "approved_at"]
        read_only_fields = ["status", "approved_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    
    class Meta:
        model = AuditLog
        fields = ["id", "action", "user", "changes", "timestamp"]


class AllegationSerializer(serializers.ModelSerializer):
    entities = AllegationEntitySerializer(many=True, read_only=True)
    responses = ResponseSerializer(many=True, read_only=True)
    
    class Meta:
        model = Allegation
        fields = [
            "id", "title", "description", "corruption_type", "status",
            "incident_date", "location", "amount_involved", "source_url",
            "evidence_urls", "submitted_by", "is_anonymous", "created_at",
            "updated_at", "entities", "responses"
        ]
        read_only_fields = ["status", "created_at", "updated_at"]


class AllegationSubmitSerializer(serializers.ModelSerializer):
    entities = AllegationEntitySerializer(many=True)
    
    class Meta:
        model = Allegation
        fields = [
            "title", "description", "corruption_type", "incident_date",
            "location", "amount_involved", "source_url", "evidence_urls",
            "submitted_by", "is_anonymous", "entities"
        ]
    
    def create(self, validated_data):
        entities_data = validated_data.pop("entities", [])
        allegation = Allegation.objects.create(**validated_data)
        
        for entity_data in entities_data:
            AllegationEntity.objects.create(allegation=allegation, **entity_data)
        
        return allegation
