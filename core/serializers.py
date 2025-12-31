from rest_framework import serializers
from django.contrib.auth import get_user_model

from django.contrib.auth.password_validation import validate_password
from .models import Group, GroupMember, PlayerProfile, Event, Attendance, Team, TeamMember, ChatMessage, GroupInvite

User = get_user_model()
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "description", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]


class GroupMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupMember
        fields = ["id", "group", "user", "role", "joined_at"]
        read_only_fields = ["role", "joined_at"]


class PlayerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerProfile
        fields = ["id", "group", "user", "rating", "position", "can_be_gk"]
        read_only_fields = ["rating"]

class SetRatingSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "group", "title", "starts_at", "location", "format", "created_by", "created_at", "teams_generated_at"]
        read_only_fields = ["created_by", "created_at", "teams_generated_at"]


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["id", "event", "user", "status", "updated_at"]
        read_only_fields = ["user", "updated_at"]


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
        read_only_fields = ["id", "event", "user", "username", "created_at"]


class GroupInviteSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()

    class Meta:
        model = GroupInvite
        fields = ["id", "group", "code", "link", "max_uses", "uses", "expires_at", "is_active", "created_at"]
        read_only_fields = ["code", "uses", "created_at"]

    def get_link(self, obj):
        # você pode trocar pelo deep link do app (ex.: myapp://invite/{code})
        request = self.context.get("request")
        if request:
            return f"{request.scheme}://{request.get_host()}/invite/{obj.code}"
        return f"/invite/{obj.code}"

class InviteAcceptSerializer(serializers.Serializer):
    code = serializers.CharField()
    
    
class GroupInviteCreateSerializer(serializers.Serializer):
    max_uses = serializers.IntegerField(min_value=1, required=False, default=50)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)
    


class UserSerializer(serializers.ModelSerializer):
    """
    Para cadastro e retorno de usuário.
    - Aceita password no create (write_only)
    - Retorna campos seguros (não retorna senha)
    """
    password = serializers.CharField(write_only=True, required=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "first_name", "last_name"]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
        }

    def validate_password(self, value: str) -> str:
        # usa as validações padrão do Django (tamanho, comum, etc.)
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user