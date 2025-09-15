import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.conf import settings
from conversations.models import Conversation, ConversationMessage
from dmessages.models import MessageAttachment
import bleach


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat functionality
    Implements room-based messaging with security and performance optimizations
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.current_conversation = None
        self.room_group_name = None
        self.heartbeat_task = None

    async def connect(self):
        """Handle WebSocket connection with authentication and room joining"""
        self.user_id = self.scope.get('user_id')
        if not self.user_id:
            await self.close(code=4001)
            return

        await self.accept()

        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())

        await self.store_connection()

    async def disconnect(self, code):
        """Handle WebSocket disconnection and cleanup"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

        if self.room_group_name:
            await self.leave_conversation_room()

        await self.remove_connection()

    async def receive(self, text_data, bytes_data=None):
        """Handle incoming WebSocket messages"""
        try:
            if len(text_data) > settings.WEBSOCKET_MAX_MESSAGE_SIZE:
                await self.send_error("Message too large")
                return

            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'join_conversation':
                await self.handle_join_conversation(data)
            elif message_type == 'leave_conversation':
                await self.handle_leave_conversation(data)
            elif message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'edit_message':
                await self.handle_edit_message(data)
            elif message_type == 'delete_message':
                await self.handle_delete_message(data)
            elif message_type == 'typing_start':
                await self.handle_typing_start(data)
            elif message_type == 'typing_stop':
                await self.handle_typing_stop(data)
            elif message_type == 'heartbeat':
                await self.handle_heartbeat()
            else:
                await self.send_error("Unknown message type")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.send_error(f"Internal server error: {e}")

    async def handle_join_conversation(self, data):
        """Handle joining a conversation room"""
        conversation_id = data.get('conversation_id')

        if not conversation_id:
            await self.send_error("Conversation ID required")
            return

        if not await self.verify_conversation_access(conversation_id):
            await self.send_error("Access denied to conversation")
            return

        if self.room_group_name:
            await self.leave_conversation_room()

        self.current_conversation = conversation_id
        self.room_group_name = f"conversation_{conversation_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.send(text_data=json.dumps({
            'type': 'conversation_joined',
            'conversation_id': conversation_id
        }))

    async def handle_leave_conversation(self, data):
        """Handle leaving a conversation room"""
        await self.leave_conversation_room()

        await self.send(text_data=json.dumps({
            'type': 'conversation_left',
            'conversation_id': self.current_conversation
        }))

    async def handle_chat_message(self, data):
        """Handle incoming chat message"""
        if not self.room_group_name:
            await self.send_error("Not in a conversation")
            return

        content = data.get('content', '').strip()
        file_upload_id = data.get('file_upload_id')  # For large files uploaded via HTTP

        if not content and not file_upload_id:
            await self.send_error("Message content or file upload required")
            return

        if file_upload_id:
            file_info = await self.verify_file_upload(file_upload_id)
            if not file_info:
                await self.send_error("Invalid file upload reference")
                return

            content = f"[File: {file_info['filename']}]"

        sanitized_content = self.sanitize_message(content)

        message = await self.save_message(sanitized_content, file_upload_id)

        if not message:
            await self.send_error("Failed to save message")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'sender_id': message.sender_id,
                    'content': message.content,
                    'created_at': message.created_at.isoformat(),
                    'conversation_id': self.current_conversation,
                    'has_attachment': bool(file_upload_id)
                }
            }
        )

    async def handle_heartbeat(self):
        """Handle heartbeat messages"""
        await self.send(text_data=json.dumps({
            'type': 'heartbeat_response',
            'timestamp': asyncio.get_event_loop().time()
        }))

    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def leave_conversation_room(self):
        """Leave current conversation room"""
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            self.room_group_name = None
            self.current_conversation = None

    async def heartbeat_loop(self):
        """Send periodic heartbeat to keep connection alive"""
        while True:
            try:
                await asyncio.sleep(settings.WEBSOCKET_HEARTBEAT_INTERVAL)
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat',
                    'timestamp': asyncio.get_event_loop().time()
                }))
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    @database_sync_to_async
    def verify_conversation_access(self, conversation_id):
        """Verify user has access to conversation"""
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants__contains=[self.user_id]
            )
            return True
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, file_upload_id=None):
        """Save message to database"""
        try:
            conversation = Conversation.objects.get(
                conversation_id=self.current_conversation
            )

            message = ConversationMessage.objects.create(
                conversation=conversation,
                sender_id=self.user_id,
                content=content
            )

            conversation.last_message_at = message.created_at
            conversation.save()

            if file_upload_id:
                MessageAttachment.objects.create(
                    message=message,
                    file_upload_id=file_upload_id
                )

            return message
        except Exception:
            return None

    def sanitize_message(self, content):
        """Sanitize message content to prevent XSS"""
        allowed_tags = []
        allowed_attributes = {}

        sanitized = bleach.clean(
            content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )

        return sanitized

    async def store_connection(self):
        """Store connection information in Redis"""
        cache_key = f"websocket_connection:{self.user_id}"
        cache.set(cache_key, {
            'channel_name': self.channel_name,
            'connected_at': asyncio.get_event_loop().time()
        }, settings.WEBSOCKET_CONNECTION_TIMEOUT)

    async def remove_connection(self):
        """Remove connection information from Redis"""
        cache_key = f"websocket_connection:{self.user_id}"
        cache.delete(cache_key)

    @database_sync_to_async
    def verify_file_upload(self, file_upload_id):
        """Verify file upload exists and belongs to user"""
        try:
            # Check cache for file upload info
            cache_key = f"file_upload:{file_upload_id}"
            file_info = cache.get(cache_key)

            if not file_info or file_info.get('user_id') != self.user_id:
                return None

            return file_info
        except Exception:
            return None

    async def handle_edit_message(self, data):
        """Handle editing a message"""
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()

        if not message_id or not new_content:
            await self.send_error("Message ID and content required")
            return

        if not self.room_group_name:
            await self.send_error("Not in a conversation")
            return

        message = await self.edit_message(message_id, new_content)
        if not message:
            await self.send_error("Failed to edit message")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_edited',
                'message': {
                    'id': message.id,
                    'sender_id': message.sender_id,
                    'content': message.content,
                    'edited_at': message.edited_at.isoformat(),
                    'conversation_id': self.current_conversation,
                    'is_edited': True
                }
            }
        )

    async def handle_delete_message(self, data):
        """Handle deleting a message"""
        message_id = data.get('message_id')

        if not message_id:
            await self.send_error("Message ID required")
            return

        if not self.room_group_name:
            await self.send_error("Not in a conversation")
            return

        success = await self.delete_message(message_id)
        if not success:
            await self.send_error("Failed to delete message")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_deleted',
                'message_id': message_id,
                'conversation_id': self.current_conversation
            }
        )

    async def handle_typing_start(self, data):
        """Handle typing start indicator"""
        if not self.room_group_name:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_start',
                'user_id': self.user_id,
                'conversation_id': self.current_conversation
            }
        )

    async def handle_typing_stop(self, data):
        """Handle typing stop indicator"""
        if not self.room_group_name:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_stop',
                'user_id': self.user_id,
                'conversation_id': self.current_conversation
            }
        )

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        """Edit message in database"""
        try:
            message = ConversationMessage.objects.get(
                id=message_id,
                sender_id=self.user_id,
                conversation__conversation_id=self.current_conversation
            )

            from django.utils import timezone
            from datetime import timedelta

            if message.created_at < timezone.now() - timedelta(hours=24):
                return None

            message.content = new_content
            message.is_edited = True
            message.edited_at = timezone.now()
            message.save()

            return message
        except ConversationMessage.DoesNotExist:
            return None
        except Exception:
            return None

    @database_sync_to_async
    def delete_message(self, message_id):
        """Delete message in database (soft delete)"""
        try:
            message = ConversationMessage.objects.get(
                id=message_id,
                sender_id=self.user_id,
                conversation__conversation_id=self.current_conversation
            )

            message.is_deleted = True
            message.deleted_at = timezone.now()
            message.save()

            return True
        except ConversationMessage.DoesNotExist:
            return False
        except Exception:
            return False
