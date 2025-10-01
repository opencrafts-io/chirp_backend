# users/consumers.py
from event_bus.consumer import BaseConsumer
from event_bus.registry import register
from django.conf import settings
from .models import User
import json
import uuid


@register
class VerisafeUserCreatedEventConsumer(BaseConsumer):
    queue_name = "io.opencrafts.chirp.verisafe.user.created"
    exchange_name = "verisafe.exchange"
    exchange_type = "direct"
    routing_key = "verisafe.user.created"

    def handle_message(self, body: str, routing_key=None):
        """
        Handle incoming created user event from Verisafe.
        body: JSON string containing the event
        """
        try:
            print(body)
            event = json.loads(body)
        except json.JSONDecodeError:
            print(f"[UserEventConsumer] Failed to decode message: {body}")
            return

        event_type = routing_key
        payload = event.get("payload", {})
        try:
            User.objects.update_or_create(
                user_id=uuid.UUID(payload["user_id"]),
                defaults={
                    "name": payload.get("name"),
                    "username": payload.get("username"),
                    "email": payload.get("email"),
                    "phone": payload.get("phone"),
                    "avatar_url": payload.get("avatar_url"),
                    "vibe_points": payload.get("vibe_points", 0),
                },
            )
            print(
                f"[VerisafeUserCreatedEventConsumer] Created user {payload.get('username')}"
            )

        except Exception as e:
            print(e)


@register
class VerisafeUserUpdatedEventConsumer(BaseConsumer):
    queue_name = "io.opencrafts.chirp.verisafe.user.updated"
    exchange_name = "verisafe.exchange"
    exchange_type = "direct"
    routing_key = "verisafe.user.updated"

    def handle_message(self, body: str, routing_key=None):
        """
        Handle incoming created user event from Verisafe.
        body: JSON string containing the event
        """
        try:
            print(body)
            event = json.loads(body)
        except json.JSONDecodeError:
            print(f"[UserEventConsumer] Failed to decode message: {body}")
            return

        event_type = routing_key
        payload = event.get("payload", {})
        try:
            User.objects.update_or_create(
                user_id=uuid.UUID(payload["user_id"]),
                defaults={
                    "name": payload.get("name"),
                    "username": payload.get("username"),
                    "email": payload.get("email"),
                    "phone": payload.get("phone"),
                    "avatar_url": payload.get("avatar_url"),
                    "vibe_points": payload.get("vibe_points", 0),
                },
            )
            print(
                f"[VerisafeUserUpdatedEventConsumer] Updated user {payload.get('username')}"
            )

        except Exception as e:
            print(e)


@register
class VerisafeUserDeletedEventConsumer(BaseConsumer):
    queue_name = "io.opencrafts.chirp.verisafe.user.deleted"
    exchange_name = "verisafe.exchange"
    exchange_type = "direct"
    routing_key = "verisafe.user.deleted"

    def handle_message(self, body: str, routing_key=None):
        """
        Handle incoming created user event from Verisafe.
        body: JSON string containing the event
        """
        try:
            print(body)
            event = json.loads(body)
        except json.JSONDecodeError:
            print(f"[UserEventConsumer] Failed to decode message: {body}")
            return

        event_type = routing_key
        payload = event.get("payload", {})
        try:

            User.objects.filter(user_id=uuid.UUID(payload["user_id"])).delete()
            print(
                f"[VerisafeUserDeletedEventConsumer] Created user {payload.get('username')}"
            )

        except Exception as e:
            print(e)
