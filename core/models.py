import secrets
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Group(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="groups_created")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MEMBER = "MEMBER", "Member"

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")



class PlayerProfile(models.Model):
    POSITION_CHOICES = [("GK", "Goleiro"), ("DF", "Defesa"), ("MF", "Meio"), ("FW", "Ataque")]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="player_profiles")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="player_profiles")
    rating = models.IntegerField(default=3)  # admin define
    position = models.CharField(max_length=2, choices=POSITION_CHOICES, default="MF")
    can_be_gk = models.BooleanField(default=False)

    class Meta:
        unique_together = ("group", "user")


class Event(models.Model):
    FORMAT_CHOICES = [
        ("FUTSAL", "Futsal (1 GK + 4)"),
        ("FUT7", "Futebol 7 (1 GK + 6)"),
        ("FUT11", "Futebol 11 (1 GK + 10)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=140)
    starts_at = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    format = models.CharField(max_length=6, choices=FORMAT_CHOICES, default="FUTSAL")

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events_created")
    created_at = models.DateTimeField(auto_now_add=True)
    teams_generated_at = models.DateTimeField(null=True, blank=True)

    def field_players_per_team(self) -> int:
        return 4 if self.format == "FUTSAL" else (6 if self.format == "FUT7" else 10)

    def players_per_team_with_gk(self) -> int:
        return self.field_players_per_team() + 1


class Attendance(models.Model):
    STATUS_CHOICES = [("GO", "Vou"), ("MAYBE", "Talvez"), ("NO", "Não vou")]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendances")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendances")
    status = models.CharField(max_length=6, choices=STATUS_CHOICES, default="NO")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("event", "user")


class Team(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_rating = models.IntegerField(default=0)


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    player_profile = models.ForeignKey(PlayerProfile, on_delete=models.SET_NULL, null=True, blank=True)
    is_goalkeeper = models.BooleanField(default=False)

    class Meta:
        unique_together = ("team", "user")


class ChatMessage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="chat_messages")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_messages")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

def generate_invite_code():
    # 8 chars base32-ish (sem caracteres confusos). Ajuste como quiser.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))

class GroupInvite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey("core.Group", on_delete=models.CASCADE, related_name="invites")
    code = models.CharField(max_length=12, unique=True, db_index=True, default=generate_invite_code)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invites_created")
    created_at = models.DateTimeField(auto_now_add=True)

    max_uses = models.PositiveIntegerField(default=50)
    uses = models.PositiveIntegerField(default=0)

    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.uses >= self.max_uses:
            return False
        return True