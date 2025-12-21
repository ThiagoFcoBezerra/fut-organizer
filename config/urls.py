from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.views import (
    GroupViewSet, GroupMemberViewSet, PlayerProfileViewSet,
    EventViewSet, AttendanceViewSet, TeamViewSet, EventChatMessagesView
)

router = DefaultRouter()
router.register(r"groups", GroupViewSet, basename="groups")
router.register(r"group-members", GroupMemberViewSet, basename="group-members")
router.register(r"player-profiles", PlayerProfileViewSet, basename="player-profiles")
router.register(r"events", EventViewSet, basename="events")
router.register(r"attendances", AttendanceViewSet, basename="attendances")
router.register(r"teams", TeamViewSet, basename="teams")

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("api/", include(router.urls)),
    path("api/events/<uuid:event_id>/chat/messages/", EventChatMessagesView.as_view()),
]
