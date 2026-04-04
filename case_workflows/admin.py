from django.contrib import admin

from .models import CaseWorkflowRun


@admin.register(CaseWorkflowRun)
class CaseWorkflowRunAdmin(admin.ModelAdmin):
    list_display = [
        "case_id",
        "workflow_template_id",
        "is_complete",
        "has_failed",
        "started_at",
        "completed_at",
        "created_at",
    ]
    list_filter = [
        "workflow_template_id",
        "is_complete",
        "has_failed",
    ]
    search_fields = [
        "case_id",
        "workflow_id",
        "workflow_template_id",
    ]
    readonly_fields = [
        "workflow_id",
        "case_data",
        "work_dir",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
