# permissions.py
from rest_framework.permissions import BasePermission
from .models import GroupMember, Event, Group

class IsGroupMember(BasePermission):
    """
    Permite acesso apenas se request.user for membro do grupo relacionado ao objeto.
    Suporta objetos: Group, Event, Attendance, Team, ChatMessage, TeamMember etc.
    """
    message = "Você precisa ser membro do grupo."

    def has_object_permission(self, request, view, obj):
        user = request.user

        if isinstance(obj, Group):
            group_id = obj.id
        elif isinstance(obj, Event):
            group_id = obj.group_id
        else:
            event = getattr(obj, "event", None)
            if event is None and hasattr(obj, "team"):
                event = obj.team.event
            if event is None:
                return False
            group_id = event.group_id

        return GroupMember.objects.filter(group_id=group_id, user=user).exists()


class IsGroupAdmin(BasePermission):
    message = "Você precisa ser ADMIN do grupo."

    def has_object_permission(self, request, view, obj):
        user = request.user

        if isinstance(obj, Group):
            group_id = obj.id
        elif isinstance(obj, Event):
            group_id = obj.group_id
        else:
            event = getattr(obj, "event", None)
            if event is None and hasattr(obj, "team"):
                event = obj.team.event
            if event is None:
                return False
            group_id = event.group_id

        return GroupMember.objects.filter(
            group_id=group_id,
            user=user,
            role=GroupMember.Role.ADMIN,
        ).exists()


class IsGroupAdminForEvent(BasePermission):
    message = "Você precisa ser ADMIN do grupo deste evento."

    def has_object_permission(self, request, view, obj):
        user = request.user
        group_id = getattr(obj, "group_id", None)

        if group_id is None:
            event = getattr(obj, "event", None)
            group_id = getattr(event, "group_id", None)

        if group_id is None:
            return False

        return GroupMember.objects.filter(
            group_id=group_id,
            user=user,
            role=GroupMember.Role.ADMIN,
        ).exists()
