from rest_framework import status, generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Conversation, ConversationMessage
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    ConversationCreateSerializer,
    ConversationMessageSerializer
)
from dmessages.models import MessageAttachment
from rest_framework.views import APIView


class ConversationListView(APIView):
    """List all conversations for a specific user"""

    def get(self, request):
        """Get all conversations for the specified user"""
        # Get user_id from query parameter
        user_id = request.GET.get('user_id')

        if not user_id:
            return Response({
                'error': 'user_id query parameter is required',
                'example': 'GET /conversations/?user_id=default_user_123'
            }, status=status.HTTP_400_BAD_REQUEST)

        conversations = Conversation._default_manager.filter(
            participants__contains=[user_id]
        ).prefetch_related(
            'messages'
        ).order_by('-last_message_at', '-created_at')

        serializer = ConversationListSerializer(
            conversations,
            many=True,
            context={'request': request, 'user_id': user_id}
        )

        return Response({
            'user_id': user_id,
            'results': serializer.data,
            'total_count': conversations.count()
        })


class ConversationDetailView(APIView):
    """Get conversation details and messages"""

    def get(self, request, conversation_id):
        """Get conversation details and recent messages"""
        # Get user_id from query parameter
        user_id = request.GET.get('user_id')

        if not user_id:
            return Response({
                'error': 'user_id query parameter is required',
                'example': 'GET /conversations/{conversation_id}/?user_id=default_user_123'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            conversation = Conversation._default_manager.get(conversation_id=conversation_id)
        except Conversation.DoesNotExist:  # type: ignore
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if user is participant
        if user_id not in conversation.participants:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        messages = ConversationMessage._default_manager.filter(
            conversation=conversation
        ).select_related('conversation').prefetch_related(
            'attachments'
        ).order_by('-created_at')[:50]

        messages = list(reversed(messages))

        conversation_serializer = ConversationSerializer(conversation, context={'request': request})
        message_serializer = ConversationMessageSerializer(messages, many=True, context={'request': request})

        return Response({
            'conversation_id': conversation.conversation_id,
            'participants': conversation.participants,
            'messages': message_serializer.data,
            'total_messages': ConversationMessage._default_manager.filter(conversation=conversation).count()
        })


class ConversationCreateView(APIView):
    """Create a new conversation between two users or find existing one"""

    def post(self, request):
        """Create or find conversation between two users"""
        # Get user_id from query parameter
        user_id = request.GET.get('user_id')

        if not user_id:
            return Response({
                'error': 'user_id query parameter is required',
                'example': 'POST /conversations/create/?user_id=default_user_123'
            }, status=status.HTTP_400_BAD_REQUEST)

        participants = request.data.get('participants', [])

        if isinstance(participants, str):
            participants = [participants]

        if user_id not in participants:
            participants.append(user_id)

        if len(participants) < 2:
            return Response({'error': 'At least 2 participants required'}, status=status.HTTP_400_BAD_REQUEST)

        existing_conversation = Conversation._default_manager.filter(
            participants__contains=participants
        ).first()

        if existing_conversation:
            serializer = ConversationSerializer(existing_conversation, context={'request': request})
            return Response({
                'message': 'Conversation found',
                'conversation': serializer.data,
                'is_new': False
            }, status=status.HTTP_200_OK)

        # Create new conversation
        conversation_data = {
            'participants': participants,
            'participant_names': [f"User {pid}" for pid in participants],
            'created_by': user_id
        }

        serializer = ConversationCreateSerializer(data=conversation_data)
        if serializer.is_valid():
            conversation = serializer.save()

            return Response({
                'message': 'Conversation created successfully',
                'conversation': ConversationSerializer(conversation, context={'request': request}).data,
                'is_new': True
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConversationMessagesView(generics.ListCreateAPIView):
    """
    Get messages for a specific conversation and create new messages
    """
    serializer_class = ConversationMessageSerializer

    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_id')
        user_id = self.request.GET.get('user_id')
        if not user_id:
            return ConversationMessage._default_manager.none()

        # Verify user is part of the conversation
        conversation = get_object_or_404(
            Conversation,
            conversation_id=conversation_id,
            participants__contains=[user_id]
        )

        return ConversationMessage._default_manager.filter(conversation=conversation)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user_id = self.request.GET.get('user_id')
        if not user_id:
            user_id = "default_user_123"
        context['user_id'] = user_id
        return context

    def create(self, request, *args, **kwargs):
        conversation_id = self.kwargs.get('conversation_id')
        user_id = request.GET.get('user_id')

        if not user_id:
            return Response({
                'error': 'user_id query parameter is required',
                'example': 'POST /conversations/{conversation_id}/messages/?user_id=default_user_123'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify user is part of the conversation
        conversation = get_object_or_404(
            Conversation,
            conversation_id=conversation_id,
            participants__contains=[user_id]
        )

        # Validate content or attachments
        content_present = request.data.get('content', '').strip()
        attachments_present = bool(request.FILES.getlist('attachments'))

        if not content_present and not attachments_present:
            return Response(
                {"detail": "Message must have content or at least one attachment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the message
        message_data = {
            'conversation': conversation.id,
            'sender_id': user_id,
            'content': request.data.get('content', '')
        }

        serializer = self.get_serializer(data=message_data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()

        # Handle file uploads
        files = request.FILES.getlist('attachments')
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

            MessageAttachment._default_manager.create(
                conversation_message=message,
                file=file,
                attachment_type=attachment_type
            )

        # Update conversation's last_message_at
        conversation.last_message_at = message.created_at
        conversation.save()

        # Return response with attachments
        response_serializer = self.get_serializer(message)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
