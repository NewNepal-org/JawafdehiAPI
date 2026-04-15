from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CaseWorkflowRunViewSet, EligibleCasesView

router = DefaultRouter()
router.register("runs", CaseWorkflowRunViewSet, basename="caseworkflowrun")

urlpatterns = [
    path("", include(router.urls)),
    path("eligible-cases/", EligibleCasesView.as_view(), name="eligible-cases"),
]
