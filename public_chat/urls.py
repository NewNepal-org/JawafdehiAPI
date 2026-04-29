from django.urls import path

from .views import PublicChatView

urlpatterns = [
    path("public/", PublicChatView.as_view(), name="public-chat"),
]
