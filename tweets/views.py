from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Tweets
from .serializers import StatusSerializer, ReplySerializer

class TweetsListCreateView(APIView):
    def get(self, request):
        # Require authentication for viewing tweets
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        tweets = Tweets.objects.all()
        serializer = StatusSerializer(tweets, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Require authentication for posting
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.copy()
        serializer = StatusSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user_id=request.user_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TweetReplyListCreateView(APIView):
    def get(self, request, tweet_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        parent_tweet = get_object_or_404(Tweets, id=tweet_id)
        replies = parent_tweet.replies.order_by('-created_at')
        serializer = ReplySerializer(replies, many=True)
        return Response(serializer.data)

    def post(self, request, tweet_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        parent_tweet = get_object_or_404(Tweets, id=tweet_id)
        serializer = ReplySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_id=request.user_id, parent_tweet=parent_tweet)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)