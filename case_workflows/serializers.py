from rest_framework import serializers

from .models import CaseWorkflowRun


class CaseWorkflowRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseWorkflowRun
        fields = [
            "run_id",
            "case_id",
            "workflow_id",
            "is_complete",
            "has_failed",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields


class CaseWorkflowRunDetailSerializer(CaseWorkflowRunSerializer):
    class Meta(CaseWorkflowRunSerializer.Meta):
        fields = CaseWorkflowRunSerializer.Meta.fields + [
            "work_dir",
            "case_data",
            "updated_at",
        ]
        read_only_fields = fields


class CaseWorkflowResumeSerializer(serializers.Serializer):
    from_step = serializers.CharField(required=False, allow_blank=False)
