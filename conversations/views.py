from rest_framework import status, generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Conversation, ConversationMessage
from .serializers import (
    ConversationSerializer,
    ConversationCreateSerializer,
    ConversationMessageSerializer
)
from dmessages.models import MessageAttachment
from rest_framework.views import APIView


class ConversationListView(APIView):
    """List all conversations for the authenticated user"""

    def get(self, request):
        """Get all conversations for the user"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        user_id = request.user_id

        # Get conversations where user is a participant
        conversations = Conversation.objects.filter(
            participants__contains=[user_id]
        ).order_by('-updated_at')

        # Get last message for each conversation
        for conversation in conversations:
            last_message = ConversationMessage.objects.filter(
                conversation=conversation
            ).order_by('-created_at').first()

            if last_message:
                conversation.last_message = last_message
                conversation.last_message_time = last_message.created_at

        serializer = ConversationSerializer(conversations, many=True, context={'request': request})

        return Response({
            'conversations': serializer.data,
            'total_count': conversations.count()
        })


class ConversationDetailView(APIView):
    """Get conversation details and messages"""

    def get(self, request, conversation_id):
        """Get conversation details and recent messages"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.user_id

        # Check if user is participant
        if user_id not in conversation.participants:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        # Get recent messages (last 50)
        messages = ConversationMessage.objects.filter(
            conversation=conversation
        ).order_by('-created_at')[:50]

        # Reverse to show oldest first
        messages = list(reversed(messages))

        conversation_serializer = ConversationSerializer(conversation, context={'request': request})
        message_serializer = ConversationMessageSerializer(messages, many=True, context={'request': request})

        return Response({
            'conversation': conversation_serializer.data,
            'messages': message_serializer.data,
            'total_messages': ConversationMessage.objects.filter(conversation=conversation).count()
        })


class ConversationCreateView(APIView):
    """Create a new conversation between two users or find existing one"""

    def post(self, request):
        """Create or find conversation between two users"""
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        user_id = request.user_id
        other_user_id = request.data.get('other_user_id')
        other_user_name = request.data.get('other_user_name', f"User {other_user_id}")

        if not other_user_id:
            return Response({'error': 'other_user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        if user_id == other_user_id:
            return Response({'error': 'Cannot create conversation with yourself'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if conversation already exists
        existing_conversation = Conversation.objects.filter(
            participants__contains=[user_id, other_user_id]
        ).first()

        if existing_conversation:
            # Return existing conversation
            serializer = ConversationSerializer(existing_conversation, context={'request': request})
            return Response({
                'message': 'Conversation found',
                'conversation': serializer.data,
                'is_new': False
            }, status=status.HTTP_200_OK)

        # Create new conversation
        conversation_data = {
            'participants': [user_id, other_user_id],
            'participant_names': [getattr(request, 'user_name', f"User {user_id}"), other_user_name],
            'created_by': user_id
        }

        serializer = ConversationSerializer(data=conversation_data)
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
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"

        # Verify user is part of the conversation
        conversation = get_object_or_404(
            Conversation,
            conversation_id=conversation_id,
            participants__contains=[user_id]
        )

        return ConversationMessage.objects.filter(conversation=conversation)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"
        context['user_id'] = user_id
        return context

    def create(self, request, *args, **kwargs):
        conversation_id = self.kwargs.get('conversation_id')
        user_id = getattr(request, 'user_id', None)

        if not user_id:
            user_id = "default_user_123"

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

            MessageAttachment.objects.create(
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
