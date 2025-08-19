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
