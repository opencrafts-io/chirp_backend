from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Message, MessageAttachment
from .serializers import MessageSerializer

class MessageListCreateView(APIView):
    def get(self, request):
        # Require authentication for viewing messages
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        messages = Message.objects.filter(recipient_id=request.user_id)
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

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

            # Handle file uploads
            files = request.FILES.getlist("attachments")
            for file in files:
                attachment_type = "image" if "image" in file.content_type else "file"
                if "video" in file.content_type:
                    attachment_type = "video"
                elif "audio" in file.content_type:
                    attachment_type = "audio"

                MessageAttachment.objects.create(
                    message=message, file=file, attachment_type=attachment_type
                )

            response_serializer = MessageSerializer(message)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
