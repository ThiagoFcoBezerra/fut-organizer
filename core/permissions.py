from rest_framework import permissions
from .models import GroupMember


class IsGroupAdminForEvent(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return GroupMember.objects.filter(group=obj.group, user=request.user, role="ADMIN").exists()
