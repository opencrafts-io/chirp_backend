from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Attachment, Post, Comment, PostLike
from .serializers import CommentSerializer, PostSerializer
from django.db.models import Exists, F, OuterRef, Q
from chirp.permissions import require_permission, CommunityPermission
from groups.models import Group
from rest_framework.exceptions import ValidationError, PermissionDenied


class PostCreateView(generics.CreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [CommunityPermission]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_id = self.kwargs.get('group_id')
        if not group_id:
            return Response(
                {"detail": "group_id is required in URL path."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {"detail": "Group not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not group.can_post(request.user_id):
            return Response(
                {"detail": "You cannot post in this community."},
                status=status.HTTP_403_FORBIDDEN,
            )

        content_present = "content" in serializer.validated_data and serializer.validated_data["content"].strip()
        attachments_present = bool(request.FILES.getlist("attachments"))

        if not content_present and not attachments_present:
            return Response(
                {"detail": "Post must have content or at least one attachment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content = serializer.validated_data.get("content", "")

        # Get user information from request body or fallback to JWT data
        user_name = serializer.validated_data.get('user_name', getattr(request, 'user_name', f"User {request.user_id}"))
        email = serializer.validated_data.get('email', getattr(request, 'user_email', None))
        avatar_url = serializer.validated_data.get('avatar_url', getattr(request, 'avatar_url', None))

        post = serializer.save(
            user_id=self.request.user_id,
            user_name=user_name,
            email=email,
            avatar_url=avatar_url,
            group=group,
            content=content
        )

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

        response_serializer = self.get_serializer(post)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class GroupPostListView(APIView):
    """View for listing posts within a specific group"""

    def get(self, request, group_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        from chirp.pagination import StandardResultsSetPagination

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        if not group.can_view(request.user_id):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        posts = Post.objects.filter(group=group).select_related('group').prefetch_related(
            'attachments', 'comments__replies__replies__replies'
        ).order_by('-created_at')

        paginator = StandardResultsSetPagination()
        paginated_posts = paginator.paginate_queryset(posts, request)

        serializer = PostSerializer(paginated_posts, many=True)
        return paginator.get_paginated_response(serializer.data)


class PostListView(APIView):
    def get(self, request):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        from chirp.pagination import StandardResultsSetPagination

        # Get group filter from query params
        group_id = request.query_params.get('group_id')

        if group_id:
            try:
                group = Group.objects.get(id=group_id)
                # Check if user can view this group
                if not group.can_view(request.user_id):
                    return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
                posts = Post.objects.filter(group=group).select_related('group').prefetch_related(
                    'attachments', 'comments__replies__replies__replies'
                ).order_by('-created_at')
            except Group.DoesNotExist:
                return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Show posts from groups user can view
            user_id = request.user_id
            accessible_groups = Group.objects.filter(
                Q(is_private=False) |
                Q(members__contains=[user_id]) |
                Q(moderators__contains=[user_id]) |
                Q(creator_id=user_id)
            )
            posts = Post.objects.filter(group__in=accessible_groups).select_related('group').prefetch_related(
                'attachments', 'comments__replies__replies__replies'
            ).order_by('-created_at')

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

        # Validate group_id is provided
        if 'group_id' not in data:
            return Response({'error': 'group_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PostSerializer(data=data)
        if serializer.is_valid():
            # Get the group and save the post
            group_id = serializer.validated_data.get('group_id')
            if group_id:
                try:
                    group = Group.objects.get(id=group_id)
                    # Check if user can post in this community
                    if not group.can_post(request.user_id):
                        return Response({'error': 'You cannot post in this community'}, status=status.HTTP_403_FORBIDDEN)

                    # Get user information from request body or fallback to JWT data
                    user_name = serializer.validated_data.get('user_name', getattr(request, 'user_name', f"User {request.user_id}"))
                    email = serializer.validated_data.get('email', getattr(request, 'user_email', None))
                    avatar_url = serializer.validated_data.get('avatar_url', getattr(request, 'avatar_url', None))

                    serializer.save(
                        user_id=request.user_id,
                        user_name=user_name,
                        email=email,
                        avatar_url=avatar_url,
                        group=group
                    )
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                except Group.DoesNotExist:
                    return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'error': 'group_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    def get(self, request, post_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            post = Post.objects.select_related('group').prefetch_related(
                'attachments', 'comments__replies__replies__replies'
            ).get(id=post_id)
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


class CommentCreateView(generics.CreateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [CommunityPermission]

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs["post_id"])
        parent_comment_id = self.request.data.get('parent_comment_id')

        if parent_comment_id:
            parent_comment = get_object_or_404(Comment, pk=parent_comment_id, post=post)

            if parent_comment.depth >= 10:
                raise ValidationError("Maximum comment depth reached (10 levels)")

            depth = parent_comment.depth + 1
        else:
            parent_comment = None
            depth = 0

        serializer.save(
            user_id=self.request.user_id,
            user_name=self.request.data.get('user_name', getattr(self.request, 'user_name', f"User {self.request.user_id}")),
            email=self.request.data.get('email', getattr(self.request, 'user_email', None)),
            avatar_url=self.request.data.get('avatar_url', getattr(self.request, 'avatar_url', None)),
            post=post,
            parent_comment=parent_comment,
            depth=depth
        )

    def get(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        threaded_comments = post.get_threaded_comments()
        serializer = self.get_serializer(threaded_comments, many=True)
        return Response(serializer.data)


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [CommunityPermission]

    def get_object(self):
        post_id = self.kwargs.get('post_id')
        comment_id = self.kwargs.get('comment_id')
        return get_object_or_404(Comment, id=comment_id, post_id=post_id)

    def perform_update(self, serializer):
        comment = self.get_object()
        if comment.user_id != self.request.user_id:
            raise PermissionDenied("You can only edit your own comments")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user_id:
            raise PermissionDenied("You can only delete your own comments")
        instance.is_deleted = True
        instance.content = "[deleted]"
        instance.save()


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
                post.like_count = F('like_count') + 1
                post.save()
                post.refresh_from_db()
                return Response({
                    "status": "liked",
                    "like_count": post.like_count,
                    "is_liked": True
                }, status=status.HTTP_201_CREATED)
            else:
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