from rest_framework import serializers
from .models import Allegation, DocumentSource, Evidence, Timeline, Modification, Response


class DocumentSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentSource
        fields = '__all__'


class TimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timeline
        fields = '__all__'


class ModificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modification
        fields = '__all__'


class EvidenceSerializer(serializers.ModelSerializer):
    source = DocumentSourceSerializer(read_only=True)
    
    class Meta:
        model = Evidence
        fields = '__all__'


class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = '__all__'


class AllegationSerializer(serializers.ModelSerializer):
    timelines = TimelineSerializer(many=True, read_only=True)
    evidences = EvidenceSerializer(many=True, read_only=True)
    modifications = ModificationSerializer(many=True, read_only=True)
    responses = ResponseSerializer(many=True, read_only=True)
    
    class Meta:
        model = Allegation
        fields = '__all__'
