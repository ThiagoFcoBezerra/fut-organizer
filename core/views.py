from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone


from .models import Group, GroupInvite, GroupMember, PlayerProfile, Event, Attendance, Team, ChatMessage
from .serializers import (
    UserSerializer, SetRatingSerializer, GroupInviteCreateSerializer, GroupInviteSerializer, GroupSerializer, GroupMemberSerializer, InviteAcceptSerializer, PlayerProfileSerializer,
    EventSerializer, AttendanceSerializer, TeamSerializer, ChatMessageSerializer
)
from .permissions import IsGroupAdminForEvent
from .services import generate_balanced_teams_for_event

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        # pode criar conta sem estar logado
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        # Opção segura: usuário só vê/edita ele mesmo
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
        return User.objects.filter(id=user.id)
class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(memberships__user=self.request.user).distinct()

    def perform_create(self, serializer):
        with transaction.atomic():
            group = serializer.save(created_by=self.request.user)
            GroupMember.objects.get_or_create(
                group=group,
                user=self.request.user,
                defaults={"role": GroupMember.Role.ADMIN},  # ou "ADMIN"
        )

class GroupMemberViewSet(viewsets.ModelViewSet):
    queryset = GroupMember.objects.all()
    serializer_class = GroupMemberSerializer
    permission_classes = [IsAuthenticated]

class PlayerProfileViewSet(viewsets.ModelViewSet):
    queryset = PlayerProfile.objects.all()
    serializer_class = PlayerProfileSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="set-rating")
    def set_rating(self, request, pk=None):
        profile = self.get_object()

        is_admin = GroupMember.objects.filter(
            group=profile.group, user=request.user, role=GroupMember.Role.ADMIN
        ).exists()
        if not is_admin:
            return Response({"detail": "Only admins can set rating."}, status=status.HTTP_403_FORBIDDEN)

        s = SetRatingSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        profile.rating = s.validated_data["rating"]
        profile.save(update_fields=["rating"])
        return Response(PlayerProfileSerializer(profile).data, status=status.HTTP_200_OK)

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(group__memberships__user=self.request.user).distinct()

    def perform_create(self, serializer):
        group = serializer.validated_data["group"]
        is_admin = GroupMember.objects.filter(
            group=group,
            user=self.request.user,
            role=GroupMember.Role.ADMIN,
        ).exists()
        if not is_admin:
            raise PermissionDenied("Você precisa ser ADMIN para criar eventos neste grupo.")

        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsGroupAdminForEvent])
    def generate_teams(self, request, pk=None):
        event = self.get_object()
        self.check_object_permissions(request, event)

        result = generate_teams_for_event(event)
        if not result.get("created"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        teams = event.teams.prefetch_related("members__user", "members__player_profile").all()
        return Response(
            {"meta": result, "teams": TeamSerializer(teams, many=True).data},
            status=status.HTTP_200_OK,
        )

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related("event", "event__group").all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Attendance.objects.filter(
            user=self.request.user,
            event__group__memberships__user=self.request.user,
        ).distinct()

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)

        event = s.validated_data["event"]
        if not GroupMember.objects.filter(group=event.group, user=request.user).exists():
            raise PermissionDenied("Você não é membro do grupo deste evento.")

        try:
            with transaction.atomic():
                attendance = s.save(user=request.user)
            return Response(self.get_serializer(attendance).data, status=status.HTTP_201_CREATED)

        except IntegrityError:
            # já existe (unique_together event+user): atualiza status
            attendance = Attendance.objects.get(event=event, user=request.user)
            attendance.status = s.validated_data.get("status", attendance.status)
            attendance.save(update_fields=["status", "updated_at"])
            return Response(self.get_serializer(attendance).data, status=status.HTTP_200_OK)

class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Team.objects.filter(event__group__memberships__user=self.request.user).distinct()


class EventChatMessagesView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        event_id = self.kwargs["event_id"]
        return (
            ChatMessage.objects
            .filter(
                event_id=event_id,
                event__group__memberships__user=self.request.user
            )
            .select_related("user")
            .distinct()
        )

    def perform_create(self, serializer):
        event_id = self.kwargs["event_id"]

        try:
            event = Event.objects.select_related("group").get(id=event_id)
        except Event.DoesNotExist:
            raise PermissionDenied("Evento inválido.")

        is_member = GroupMember.objects.filter(
            group=event.group,
            user=self.request.user
        ).exists()

        if not is_member:
            raise PermissionDenied("Você não é membro do grupo deste evento.")

        # Garante que o cliente não forja event/user:
        serializer.save(event=event, user=self.request.user)

class GroupInviteCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)

        if not GroupMember.objects.filter(
            group=group, user=request.user, role=GroupMember.Role.ADMIN
        ).exists():
            raise PermissionDenied("Only admins can create invites.")

        s = GroupInviteCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        # cria com retry pra evitar colisão de code (muito raro)
        for _ in range(3):
            try:
                with transaction.atomic():
                    invite = GroupInvite.objects.create(
                        group=group,
                        created_by=request.user,
                        max_uses=s.validated_data["max_uses"],
                        expires_at=s.validated_data.get("expires_at"),
                        is_active=s.validated_data["is_active"],
                    )
                break
            except IntegrityError:
                invite = None

        if invite is None:
            return Response(
                {"detail": "Could not generate invite code. Try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            GroupInviteSerializer(invite, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
            
class InviteAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        s = InviteAcceptSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        code = s.validated_data["code"].strip().upper()

        try:
            invite = (
                GroupInvite.objects
                .select_for_update()
                .select_related("group")
                .get(code=code)
            )
        except GroupInvite.DoesNotExist:
            return Response({"detail": "Invalid code."}, status=status.HTTP_404_NOT_FOUND)

        if not invite.is_valid():
            return Response({"detail": "Invite expired or inactive."}, status=status.HTTP_400_BAD_REQUEST)

        group = invite.group

        member, created = GroupMember.objects.get_or_create(
            group=group,
            user=request.user,
            defaults={"role": GroupMember.Role.MEMBER},
        )

        PlayerProfile.objects.get_or_create(group=group, user=request.user)

        if created:
            GroupInvite.objects.filter(pk=invite.pk).update(uses=F("uses") + 1)

        return Response(
            {
                "group": str(group.id),
                "member_id": member.id,
                "role": member.role,
                "already_member": not created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )