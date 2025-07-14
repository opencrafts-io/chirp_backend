from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Post
from .serializers import StatusSerializer, ReplySerializer
from django.db.models import F
from .models import PostLike

class PostListCreateView(APIView):
    def get(self, request):
        # Require authentication for viewing posts
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        posts = Post.objects.all()
        serializer = StatusSerializer(posts, many=True, context={'user_id': request.user_id})
        return Response(serializer.data)

    def post(self, request):
        # Require authentication for posting
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = StatusSerializer(data=request.data, context={'user_id': request.user_id})
        if serializer.is_valid():
            serializer.save(user_id=request.user_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    def get_object(self, pk):
        return get_object_or_404(Post, pk=pk)

    def get(self, request, pk):
        post = self.get_object(pk)
        serializer = StatusSerializer(post, context={'user_id': request.user_id})
        return Response(serializer.data)

    def put(self, request, pk):
        post = self.get_object(pk)
        serializer = StatusSerializer(post, data=request.data, context={'user_id': request.user_id})
        if serializer.is_valid():
            serializer.save(user_id=post.user_id)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        post = self.get_object(pk)
        serializer = StatusSerializer(post, data=request.data, partial=True, context={'user_id': request.user_id})
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


class PostLikeToggleView(APIView):
    def post(self, request, pk):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        post = get_object_or_404(Post, pk=pk)
        like, created = PostLike.objects.get_or_create(user_id=request.user_id, post=post)

        if created:
            Post.objects.filter(pk=pk).update(like_count=F('like_count') + 1)
            return Response({'status': 'liked'}, status=status.HTTP_201_CREATED)

        return Response({'status': 'already liked'}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        post = get_object_or_404(Post, pk=pk)
        deleted_count, _ = PostLike.objects.filter(user_id=request.user_id, post=post).delete()

        if deleted_count > 0:
            Post.objects.filter(pk=pk).update(like_count=F('like_count') - 1)
            return Response({'status': 'unliked'}, status=status.HTTP_204_NO_CONTENT)

        return Response({'error': 'Not liked yet'}, status=status.HTTP_404_NOT_FOUND)