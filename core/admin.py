from django.contrib import admin
from .models import Group, GroupMember, PlayerProfile, Event, Attendance, Team, TeamMember, ChatMessage

admin.site.register(Group)
admin.site.register(GroupMember)
admin.site.register(PlayerProfile)
admin.site.register(Event)
admin.site.register(Attendance)
admin.site.register(Team)
admin.site.register(TeamMember)
admin.site.register(ChatMessage)
