from django.core.paginator import Paginator
from django.db.models import Q
from conversations.models import Conversation, ConversationMessage
from dmessages.models import MessageAttachment
from typing import Dict, List


class ChatService:
    """
    Service layer for chat operations including message history and pagination
    """

    @staticmethod
    def get_conversation_messages(conversation_id: str, user_id: str, page: int = 1, page_size: int = 50) -> Dict:
        """
        Get paginated messages for a conversation
        """
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants__contains=[user_id]
            )

            messages = ConversationMessage.objects.filter(
                conversation=conversation
            ).order_by('-created_at')

            paginator = Paginator(messages, page_size)
            page_obj = paginator.get_page(page)

            message_data = []
            for message in page_obj:
                message_info = {
                    'id': message.id,
                    'sender_id': message.sender_id,
                    'content': message.content,
                    'created_at': message.created_at.isoformat(),
                    'is_read': message.is_read,
                    'attachments': []
                }

                attachments = MessageAttachment.objects.filter(
                    conversation_message=message
                )
                for attachment in attachments:
                    message_info['attachments'].append({
                        'id': attachment.id,
                        'file_url': attachment.get_file_url(),
                        'file_size_mb': attachment.get_file_size_mb(),
                        'attachment_type': attachment.attachment_type,
                        'original_filename': attachment.original_filename
                    })

                message_data.append(message_info)

            return {
                'messages': message_data,
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': paginator.num_pages,
                    'total_messages': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                    'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
                    'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None
                }
            }

        except Conversation.DoesNotExist:
            return {'error': 'Conversation not found or access denied'}
        except Exception as e:
            return {'error': f'Failed to retrieve messages: {str(e)}'}

    @staticmethod
    def mark_messages_as_read(conversation_id: str, user_id: str, message_ids: List[int] = None) -> Dict:
        """
        Mark messages as read for a user
        """
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants__contains=[user_id]
            )

            if message_ids:
                messages = ConversationMessage.objects.filter(
                    conversation=conversation,
                    id__in=message_ids,
                    sender_id__ne=user_id  # Don't mark own messages as read
                )
            else:
                messages = ConversationMessage.objects.filter(
                    conversation=conversation,
                    sender_id__ne=user_id,
                    is_read=False
                )

            updated_count = messages.update(is_read=True)

            return {
                'success': True,
                'messages_marked_read': updated_count
            }

        except Conversation.DoesNotExist:
            return {'error': 'Conversation not found or access denied'}
        except Exception as e:
            return {'error': f'Failed to mark messages as read: {str(e)}'}

    @staticmethod
    def get_conversation_participants(conversation_id: str, user_id: str) -> Dict:
        """
        Get participants for a conversation
        """
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants__contains=[user_id]
            )

            return {
                'conversation_id': conversation.conversation_id,
                'participants': conversation.participants,
                'created_at': conversation.created_at.isoformat(),
                'last_message_at': conversation.last_message_at.isoformat() if conversation.last_message_at else None
            }

        except Conversation.DoesNotExist:
            return {'error': 'Conversation not found or access denied'}
        except Exception as e:
            return {'error': f'Failed to retrieve conversation info: {str(e)}'}

    @staticmethod
    def get_unread_message_count(conversation_id: str, user_id: str) -> int:
        """
        Get count of unread messages for a user in a conversation
        """
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants__contains=[user_id]
            )

            return ConversationMessage.objects.filter(
                conversation=conversation,
                sender_id__ne=user_id,
                is_read=False
            ).count()

        except Conversation.DoesNotExist:
            return 0
        except Exception:
            return 0
