from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
import os
from .services import ChatService
from conversations.models import Conversation


class FileUploadView(APIView):
    """
    HTTP endpoint for uploading large files (images, videos, etc.)
    This handles files that are too large for WebSocket messages
    """

    def post(self, request, conversation_id):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        # Verify user has access to conversation
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants__contains=[request.user_id]
            )
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

        # Check if file was uploaded
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES['file']

        # Validate file size (e.g., 50MB max for videos, 10MB for images)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_obj.size > max_size:
            return Response({'error': 'File too large. Maximum size is 50MB'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/avi', 'video/mov']
        if file_obj.content_type not in allowed_types:
            return Response({'error': 'File type not allowed'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Generate unique filename
            file_extension = os.path.splitext(file_obj.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"

            # Save file
            file_path = f"message_attachments/{conversation_id}/{unique_filename}"
            saved_path = default_storage.save(file_path, ContentFile(file_obj.read()))

            # Create temporary file record
            file_upload_id = str(uuid.uuid4())

            # Store file info in cache for WebSocket reference
            from django.core.cache import cache
            cache.set(
                f"file_upload:{file_upload_id}",
                {
                    'filename': file_obj.name,
                    'file_path': saved_path,
                    'file_size': file_obj.size,
                    'content_type': file_obj.content_type,
                    'user_id': request.user_id,
                    'conversation_id': conversation_id
                },
                timeout=3600  # 1 hour
            )

            return Response({
                'file_upload_id': file_upload_id,
                'filename': file_obj.name,
                'file_size': file_obj.size,
                'content_type': file_obj.content_type
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'Failed to upload file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConversationMessagesHistoryView(APIView):
    """
    HTTP endpoint for retrieving message history with pagination
    This complements the WebSocket real-time messaging
    """

    def get(self, request, conversation_id):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))

        # Get messages using service
        result = ChatService.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=request.user_id,
            page=page,
            page_size=page_size
        )

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class MarkMessagesAsReadView(APIView):
    """
    HTTP endpoint for marking messages as read
    """

    def post(self, request, conversation_id):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        # Get message IDs to mark as read (optional)
        message_ids = request.data.get('message_ids', None)

        # Mark messages as read using service
        result = ChatService.mark_messages_as_read(
            conversation_id=conversation_id,
            user_id=request.user_id,
            message_ids=message_ids
        )

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class ConversationInfoView(APIView):
    """
    HTTP endpoint for getting conversation information
    """

    def get(self, request, conversation_id):
        # Require authentication
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        # Get conversation info using service
        result = ChatService.get_conversation_participants(
            conversation_id=conversation_id,
            user_id=request.user_id
        )

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        # Add unread message count
        result['unread_count'] = ChatService.get_unread_message_count(
            conversation_id=conversation_id,
            user_id=request.user_id
        )

        return Response(result, status=status.HTTP_200_OK)
