from rest_framework import serializers
from .models import Group, GroupMember, PlayerProfile, Event, Attendance, Team, TeamMember, ChatMessage


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "description", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]


class GroupMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupMember
        fields = ["id", "group", "user", "role", "joined_at"]
        read_only_fields = ["joined_at"]


class PlayerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerProfile
        fields = ["id", "group", "user", "rating", "position", "can_be_gk"]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "group", "title", "starts_at", "location", "format", "created_by", "created_at", "teams_generated_at"]
        read_only_fields = ["created_by", "created_at", "teams_generated_at"]


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["id", "event", "user", "status", "updated_at"]
        read_only_fields = ["updated_at"]


class TeamMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = TeamMember
        fields = ["id", "user", "username", "is_goalkeeper"]


class TeamSerializer(serializers.ModelSerializer):
    members = TeamMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ["id", "event", "name", "total_rating", "members"]


class ChatMessageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ChatMessage
        fields = ["id", "event", "user", "username", "text", "created_at"]
        read_only_fields = ["id", "user", "username", "created_at"]
