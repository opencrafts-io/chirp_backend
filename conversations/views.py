from rest_framework import status, generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Conversation, ConversationMessage
from .serializers import (
    ConversationSerializer,
    ConversationCreateSerializer,
    ConversationMessageSerializer
)


class ConversationListView(generics.ListAPIView):
    """
    Get all conversations for the authenticated user
    """
    serializer_class = ConversationSerializer

    def get_queryset(self):
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"
        return Conversation.objects.filter(participants__contains=[user_id])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"
        context['user_id'] = user_id
        return context


class ConversationDetailView(generics.RetrieveAPIView):
    """
    Get conversation details
    """
    serializer_class = ConversationSerializer
    lookup_field = 'conversation_id'

    def get_queryset(self):
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"
        return Conversation.objects.filter(participants__contains=[user_id])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            user_id = "default_user_123"
        context['user_id'] = user_id
        return context


class ConversationCreateView(generics.CreateAPIView):
    """
    Create a new conversation
    """
    serializer_class = ConversationCreateSerializer

    def create(self, request, *args, **kwargs):
        user_id = getattr(request, 'user_id', None)
        participants = request.data.get('participants', [])

        # For testing purposes, use a default user if not authenticated
        if not user_id:
            user_id = "default_user_123"

        # Ensure participants is a list
        if not isinstance(participants, list):
            participants = [participants] if participants else []

        # Ensure the current user is included in participants
        if user_id not in participants:
            participants.append(user_id)

        # Check if conversation already exists between these participants
        existing_conversation = Conversation.objects.filter(
            participants__contains=participants
        ).first()

        if existing_conversation:
            serializer = ConversationSerializer(existing_conversation, context={'user_id': user_id})
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Create new conversation
        serializer = self.get_serializer(data={'participants': participants})
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()

        response_serializer = ConversationSerializer(conversation, context={'user_id': user_id})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


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

    def create(self, request, *args, **kwargs):
        conversation_id = self.kwargs.get('conversation_id')
        user_id = getattr(request, 'user_id', None)

        # For testing purposes, use a default user if not authenticated
        if not user_id:
            user_id = "default_user_123"

        # Verify user is part of the conversation
        conversation = get_object_or_404(
            Conversation,
            conversation_id=conversation_id,
            participants__contains=[user_id]
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

        # Update conversation's last_message_at
        conversation.last_message_at = message.created_at
        conversation.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
