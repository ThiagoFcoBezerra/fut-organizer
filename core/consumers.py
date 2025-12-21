import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Event, ChatMessage, GroupMember


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", AnonymousUser())
        if not user or user.is_anonymous:
            await self.close(code=4401)
            return

        self.event_id = self.scope["url_route"]["kwargs"]["event_id"]
        self.room = f"event_chat_{self.event_id}"

        ok = await self._can_access(user.id, self.event_id)
        if not ok:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room"):
            await self.channel_layer.group_discard(self.room, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        payload = json.loads(text_data or "{}")
        text = (payload.get("text") or "").strip()
        if not text:
            return
        if len(text) > 1000:
            await self.send(text_data=json.dumps({"type": "error", "detail": "Mensagem muito longa."}))
            return

        msg = await self._create_message(self.event_id, self.scope["user"].id, text)

        await self.channel_layer.group_send(self.room, {
            "type": "chat.message",
            **msg,
        })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @sync_to_async
    def _can_access(self, user_id, event_id) -> bool:
        try:
            ev = Event.objects.select_related("group").get(id=event_id)
        except Event.DoesNotExist:
            return False
        return GroupMember.objects.filter(group=ev.group, user_id=user_id).exists()

    @sync_to_async
    def _create_message(self, event_id, user_id, text):
        ev = Event.objects.get(id=event_id)
        m = ChatMessage.objects.create(event=ev, user_id=user_id, text=text)
        return {
            "type": "chat.message",
            "id": m.id,
            "event_id": str(event_id),
            "user_id": user_id,
            "username": m.user.username,
            "text": m.text,
            "created_at": m.created_at.isoformat(),
        }
