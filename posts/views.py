from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Attachment, Post, PostLike, PostReply
from .serializers import PostReplySerializer, PostSerializer
from django.db.models import Exists, F, OuterRef
from chirp.permissions import require_permission


class PostCreateView(generics.CreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content_present = "content" in serializer.validated_data and serializer.validated_data["content"].strip()
        attachments_present = bool(request.FILES.getlist("attachments"))

        if not content_present and not attachments_present:
            return Response(
                {"detail": "Post must have content or at least one attachment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content = serializer.validated_data.get("content", "")
        post = serializer.save(user_id=self.request.user_id, content=content)

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

            Attachment.objects.create(
                post=post,
                file=file,
                attachment_type=attachment_type
            )

        # Return response with attachments
        response_serializer = self.get_serializer(post)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class PostListView(APIView):
    def get(self, request):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        from chirp.pagination import StandardResultsSetPagination

        posts = Post.objects.all().order_by('-created_at')

        # Apply pagination
        paginator = StandardResultsSetPagination()
        paginated_posts = paginator.paginate_queryset(posts, request)

        serializer = PostSerializer(paginated_posts, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.copy()
        data['user_id'] = request.user_id
        serializer = PostSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    def get(self, request, post_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            post = Post.objects.get(id=post_id)
            serializer = PostSerializer(post)
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, post_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            post = Post.objects.get(id=post_id, user_id=request.user_id)
            serializer = PostSerializer(post, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, post_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            post = Post.objects.get(id=post_id, user_id=request.user_id)
            post.delete()
            return Response({'message': 'Post deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)


class PostReplyCreateView(generics.CreateAPIView):
    queryset = PostReply.objects.all()
    serializer_class = PostReplySerializer

    def perform_create(self, serializer):
        parent_post = get_object_or_404(Post, pk=self.kwargs["post_id"])
        serializer.save(user_id=self.request.user_id, parent_post=parent_post)

    def get(self, request, post_id):
        from chirp.pagination import StandardResultsSetPagination

        replies = PostReply.objects.filter(parent_post_id=post_id).order_by("-created_at")

        # Apply pagination
        paginator = StandardResultsSetPagination()
        paginated_replies = paginator.paginate_queryset(replies, request)

        serializer = self.get_serializer(paginated_replies, many=True)
        return paginator.get_paginated_response(serializer.data)


class PostLikeView(APIView):
    def post(self, request, post_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            post = Post.objects.get(id=post_id)
            like, created = PostLike.objects.get_or_create(
                post=post,
                user_id=request.user_id
            )

            if created:
                post.like_count = F('like_count') + 1
                post.save()
                post.refresh_from_db()
                return Response({"status": "liked"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"status": "already liked"}, status=status.HTTP_400_BAD_REQUEST)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, post_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            post = Post.objects.get(id=post_id)
            like = PostLike.objects.get(post=post, user_id=request.user_id)
            like.delete()

            post.like_count = F('like_count') - 1
            post.save()
            post.refresh_from_db()

            return Response({"status": "unliked"}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        except PostLike.DoesNotExist:
            return Response({"status": "not liked"}, status=status.HTTP_404_NOT_FOUND)


class PostLikeToggleView(APIView):
    """Toggle like status for a post"""

    def post(self, request, pk):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            post = Post.objects.get(id=pk)
            like, created = PostLike.objects.get_or_create(
                post=post,
                user_id=request.user_id
            )

            if created:
                # Like the post
                post.like_count = F('like_count') + 1
                post.save()
                post.refresh_from_db()
                return Response({
                    "status": "liked",
                    "like_count": post.like_count,
                    "is_liked": True
                }, status=status.HTTP_201_CREATED)
            else:
                # Unlike the post
                like.delete()
                post.like_count = F('like_count') - 1
                post.save()
                post.refresh_from_db()
                return Response({
                    "status": "unliked",
                    "like_count": post.like_count,
                    "is_liked": False
                }, status=status.HTTP_200_OK)

        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)