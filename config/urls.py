from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import (
    GroupInviteCreateView, GroupViewSet, GroupMemberViewSet, InviteAcceptView, PlayerProfileViewSet,
    EventViewSet, AttendanceViewSet, TeamViewSet, EventChatMessagesView, UserViewSet
)

router = DefaultRouter()
router.register(r"groups", GroupViewSet, basename="groups")
router.register(r"group-members", GroupMemberViewSet, basename="group-members")
router.register(r"player-profiles", PlayerProfileViewSet, basename="player-profiles")
router.register(r"events", EventViewSet, basename="events")
router.register(r"attendances", AttendanceViewSet, basename="attendances")
router.register(r"teams", TeamViewSet, basename="teams")
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # Gera o esquema OpenAPI 3
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Interface visual do Swagger
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("api/", include(router.urls)),
    path("api/events/<uuid:event_id>/chat/messages/", EventChatMessagesView.as_view()),
    
    path("api/groups/<int:group_id>/invites/", GroupInviteCreateView.as_view()),
    path("api/invites/accept/", InviteAcceptView.as_view()),
]
