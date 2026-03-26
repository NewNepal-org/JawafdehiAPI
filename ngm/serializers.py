from rest_framework import serializers


class NGMQuerySerializer(serializers.Serializer):
    query = serializers.CharField()
    timeout = serializers.FloatField(
        required=False, min_value=1, max_value=15, default=15
    )
