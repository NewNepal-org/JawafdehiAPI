from django.apps import AppConfig


class CaseWorkflowsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "case_workflows"
    verbose_name = "Case Workflows"

    def ready(self):
        # Auto-discover workflow templates on startup
        from case_workflows.registry import autodiscover

        autodiscover()
