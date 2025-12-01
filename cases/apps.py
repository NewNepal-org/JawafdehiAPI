from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cases"

    def ready(self):
        import cases.rules  # Load permission rules on startup
        
        # Register models with auditlog
        from auditlog.registry import auditlog
        from cases.models import Case, DocumentSource, JawafEntity
        
        auditlog.register(Case)
        auditlog.register(DocumentSource)
        auditlog.register(JawafEntity)
        
        # Warn if EXPOSE_CASES_IN_REVIEW feature flag is enabled
        from django.conf import settings
        if settings.EXPOSE_CASES_IN_REVIEW:
            logger.warning(
                "⚠️  EXPOSE_CASES_IN_REVIEW feature flag is ENABLED. "
                "Cases in IN_REVIEW state are now exposed via the public API. "
                "This should only be enabled temporarily for emergency deployments."
            )
