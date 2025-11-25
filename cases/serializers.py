from rest_framework import serializers
from .models import Allegation, DocumentSource, Modification, Response


class DocumentSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentSource
        fields = '__all__'


class ModificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modification
        fields = '__all__'


class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = '__all__'


class AllegationSerializer(serializers.ModelSerializer):
    modifications = ModificationSerializer(many=True, read_only=True)
    responses = ResponseSerializer(many=True, read_only=True)
    
    class Meta:
        model = Allegation
        fields = '__all__'
