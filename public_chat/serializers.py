from rest_framework import serializers


class PublicChatHistoryItemSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(allow_blank=False, trim_whitespace=True)


class PublicChatRequestSerializer(serializers.Serializer):
    question = serializers.CharField(allow_blank=False, trim_whitespace=True)
    session_id = serializers.CharField(required=False, allow_blank=True, max_length=200)
    history = PublicChatHistoryItemSerializer(many=True, required=False)
    language = serializers.CharField(required=False, allow_blank=True, max_length=20)


class PublicChatSourceSerializer(serializers.Serializer):
    title = serializers.CharField()
    url = serializers.CharField(allow_blank=True)
    type = serializers.CharField()
    snippet = serializers.CharField(required=False, allow_blank=True)
    source_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    document_id = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    chunk_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    page_start = serializers.IntegerField(required=False, allow_null=True)
    page_end = serializers.IntegerField(required=False, allow_null=True)
    score = serializers.FloatField(required=False, allow_null=True)


class PublicChatRelatedCaseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    url = serializers.CharField()
    slug = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    case_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    short_description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class PublicChatResponseSerializer(serializers.Serializer):
    answer_text = serializers.CharField()
    session_id = serializers.CharField(required=False)
    sources = PublicChatSourceSerializer(many=True)
    related_cases = PublicChatRelatedCaseSerializer(many=True)
    follow_up_questions = serializers.ListField(child=serializers.CharField())
