from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Message
from .serializers import MessageSerializer

class MessageListCreateView(APIView):
    def get(self, request):
        messages = Message.objects.filter(recipient_id=request.user_id)
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data['sender_id'] = request.user_id
        serializer = MessageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
