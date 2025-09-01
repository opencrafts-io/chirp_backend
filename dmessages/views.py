from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Message, MessageAttachment
from .serializers import MessageSerializer

class MessageListCreateView(APIView):
    def get(self, request):
        # Require authentication for viewing messages
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        from chirp.pagination import StandardResultsSetPagination

        messages = Message.objects.filter(recipient_id=request.user_id).order_by("-created_at")

        # Apply pagination
        paginator = StandardResultsSetPagination()
        paginated_messages = paginator.paginate_queryset(messages, request)

        serializer = MessageSerializer(paginated_messages, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Require authentication for sending messages
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.copy()
        serializer = MessageSerializer(data=data)
        if serializer.is_valid():
            content_present = serializer.validated_data.get("content", "").strip()
            attachments_present = bool(request.FILES.getlist("attachments"))

            if not content_present and not attachments_present:
                return Response(
                    {"detail": "Message must have content or at least one attachment."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            content = serializer.validated_data.get("content", "")
            message = serializer.save(sender_id=request.user_id, content=content)

            files = request.FILES.getlist("attachments")
            for file in files:
                content_type = file.content_type.lower()
                if "image" in content_type:
                    attachment_type = "image"
                elif "video" in content_type:
                    attachment_type = "video"
                elif "audio" in content_type:
                    attachment_type = "audio"
                else:
                    attachment_type = "file"

                MessageAttachment.objects.create(
                    message=message,
                    file=file,
                    attachment_type=attachment_type
                )

            # Return response with attachments
            response_serializer = MessageSerializer(message)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a message
    """
    serializer_class = MessageSerializer
    queryset = Message.objects.all()

    def get_queryset(self):
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"
        return Message.objects.filter(
            Q(sender_id=user_id) | Q(recipient_id=user_id)
        )

    def perform_update(self, serializer):
        # Only allow sender to update the message
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"
        if serializer.instance.sender_id != user_id:
            raise PermissionError("Only the sender can edit this message")
        serializer.save()

    def perform_destroy(self, instance):
        # Only allow sender to delete the message
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"
        if instance.sender_id != user_id:
            raise PermissionError("Only the sender can delete this message")
        # Soft delete by setting is_deleted flag
        instance.is_deleted = True
        instance.save()


class MessageReadView(APIView):
    """
    Mark a message as read
    """
    def put(self, request, pk):
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"
        message = get_object_or_404(
            Message,
            pk=pk,
            recipient_id=user_id,
            is_deleted=False
        )
        message.is_read = True
        message.save()
        serializer = MessageSerializer(message)
        return Response(serializer.data)


class MessageEditView(APIView):
    """Edit a specific message"""

    def put(self, request, message_id):
        """Edit message content"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        # Check if user is the message sender
        if message.sender_id != user_id:
            return Response({'error': 'You can only edit your own messages'}, status=status.HTTP_403_FORBIDDEN)

        # Check if message is too old (e.g., 24 hours)
        from django.utils import timezone
        from datetime import timedelta

        if message.created_at < timezone.now() - timedelta(hours=24):
            return Response({'error': 'Messages can only be edited within 24 hours'}, status=status.HTTP_400_BAD_REQUEST)

        new_content = request.data.get('content', '').strip()
        if not new_content:
            return Response({'error': 'Message content cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)

        # Update message
        message.content = new_content
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save()

        serializer = MessageSerializer(message, context={'request': request})
        return Response({
            'message': 'Message updated successfully',
            'message_data': serializer.data
        })


class MessageDeleteView(APIView):
    """Delete a specific message"""

    def delete(self, request, message_id):
        """Delete message"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        # Check if user is the message sender
        if message.sender_id != user_id:
            return Response({'error': 'You can only delete your own messages'}, status=status.HTTP_403_FORBIDDEN)

        # Soft delete - mark as deleted instead of removing from DB
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save()

        return Response({
            'message': 'Message deleted successfully',
            'message_id': message_id
        })


class ConversationMessageListView(APIView):
    """Get paginated messages for a conversation"""

    def get(self, request, conversation_id):
        """Get paginated messages for a conversation"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        if user_id not in conversation.participants:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))

        messages = Message.objects.filter(
            conversation=conversation,
            is_deleted=False
        ).order_by('-created_at')

        from django.core.paginator import Paginator
        paginator = Paginator(messages, page_size)

        try:
            page_obj = paginator.page(page)
        except:
            return Response({'error': 'Invalid page number'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MessageSerializer(page_obj.object_list, many=True, context={'request': request})

        return Response({
            'messages': serializer.data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_messages': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None
            }
        })
