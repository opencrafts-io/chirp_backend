from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Post
from .serializers import StatusSerializer, ReplySerializer

class PostListCreateView(APIView):
    def get(self, request):
        # Require authentication for viewing posts
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        posts = Post.objects.all()
        serializer = StatusSerializer(posts, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Require authentication for posting
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = StatusSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_id=request.user_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    def get_object(self, pk):
        return get_object_or_404(Post, pk=pk)

    def get(self, request, pk):
        post = self.get_object(pk)
        serializer = StatusSerializer(post)
        return Response(serializer.data)

    def put(self, request, pk):
        post = self.get_object(pk)
        serializer = StatusSerializer(post, data=request.data)
        if serializer.is_valid():
            serializer.save(user_id=post.user_id)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        post = self.get_object(pk)
        serializer = StatusSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(user_id=post.user_id)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        post = self.get_object(pk)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostReplyListCreateView(APIView):
    def get(self, request, post_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        parent_post = get_object_or_404(Post, id=post_id)
        replies = parent_post.replies.order_by('-created_at')
        serializer = ReplySerializer(replies, many=True)
        return Response(serializer.data)

    def post(self, request, post_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        parent_post = get_object_or_404(Post, id=post_id)
        serializer = ReplySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_id=request.user_id, parent_post=parent_post)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)