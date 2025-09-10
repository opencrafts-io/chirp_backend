from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Attachment, Post, Comment, PostLike, CommentLike
from .serializers import CommentSerializer, PostSerializer
from django.db.models import Exists, F, OuterRef, Q
from chirp.permissions import require_permission, CommunityPermission
from groups.models import Group
from rest_framework.exceptions import ValidationError, PermissionDenied
from utils.recommendation_engine import get_recommended_posts
from utils.metrics_service import metrics_service
from django.utils import timezone
import time

class PostCreateView(generics.CreateAPIView):
    queryset = Post._default_manager.all()
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
            group = Group._default_manager.get(id=group_id)
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
            group = Group._default_manager.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

        if not group.can_view(request.user_id):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        posts = Post._default_manager.filter(group=group).select_related('group').prefetch_related(
            'attachments', 'comments__replies__replies__replies'
        ).order_by('-created_at')

        paginator = StandardResultsSetPagination()
        paginated_posts = paginator.paginate_queryset(posts, request)

        serializer = PostSerializer(paginated_posts, many=True)
        return paginator.get_paginated_response(serializer.data)


class PostListView(APIView):
    def get(self, request):
        from chirp.pagination import StandardResultsSetPagination

        start_time = time.time()

        # Get query parameters
        group_id = request.query_params.get('group_id')
        use_recommendations = request.query_params.get('recommendations', 'true').lower() == 'true'
        user_id = getattr(request, 'user_id', None)

        try:
            if use_recommendations and not group_id:
                posts = self._get_recommended_posts(user_id, group_id)
                cache_hit = True
            else:
                posts = self._get_traditional_posts(request, group_id)
                cache_hit = False

            # Apply pagination
            paginator = StandardResultsSetPagination()
            paginated_posts = paginator.paginate_queryset(posts, request)

            # Serialize posts
            serializer = PostSerializer(paginated_posts, many=True)
            response = paginator.get_paginated_response(serializer.data)

            response_time = (time.time() - start_time) * 1000
            metrics_service.track_recommendation_request(
                user_id=user_id,
                group_id=int(group_id) if group_id else None,
                limit=len(paginated_posts),
                response_time=response_time,
                posts_count=len(paginated_posts),
                cache_hit=cache_hit
            )

            return response

        except Exception as e:
            posts = self._get_traditional_posts(request, group_id)
            paginator = StandardResultsSetPagination()
            paginated_posts = paginator.paginate_queryset(posts, request)
            serializer = PostSerializer(paginated_posts, many=True)
            return paginator.get_paginated_response(serializer.data)

    def _get_recommended_posts(self, user_id, group_id):
        """Get posts using the recommendation system."""
        try:
            recommended_posts = get_recommended_posts(
                user_id=user_id,
                group_id=int(group_id) if group_id else None,
                limit=50
            )

            post_ids = [post.id for post in recommended_posts]
            posts = Post.objects.filter(id__in=post_ids).select_related('group').prefetch_related(
                'attachments', 'comments__replies__replies__replies'
            )

            order_dict = {post.id: i for i, post in enumerate(recommended_posts)}
            posts_list = list(posts)
            posts_list.sort(key=lambda x: order_dict.get(x.id, 999))

            return posts_list

        except Exception as e:
            return self._get_traditional_posts_fallback(user_id, group_id)

    def _get_traditional_posts(self, request, group_id):
        """Get posts using traditional filtering."""
        if group_id:
            try:
                group = Group._default_manager.get(id=group_id)
                if group.is_private:
                    if not hasattr(request, 'user_id') or not request.user_id:
                        raise PermissionError('Authentication required for private groups')
                    if not group.can_view(request.user_id):
                        raise PermissionError('Access denied')

                return Post._default_manager.filter(group=group).select_related('group').prefetch_related(
                    'attachments', 'comments__replies__replies__replies'
                ).order_by('-created_at')
            except Group.DoesNotExist:
                raise ValueError('Group not found')
        else:
            if hasattr(request, 'user_id') and request.user_id:
                user_id = request.user_id
                accessible_groups = Group._default_manager.filter(
                    Q(is_private=False) |
                    Q(members__contains=[user_id]) |
                    Q(moderators__contains=[user_id]) |
                    Q(creator_id=user_id)
                )
                return Post._default_manager.filter(group__in=accessible_groups).select_related('group').prefetch_related(
                    'attachments', 'comments__replies__replies__replies'
                ).order_by('-created_at')
            else:
                return Post._default_manager.filter(group__is_private=False).select_related('group').prefetch_related(
                    'attachments', 'comments__replies__replies__replies'
                ).order_by('-created_at')

    def _get_traditional_posts_fallback(self, user_id, group_id):
        """Fallback method for getting posts."""
        if group_id:
            return Post._default_manager.filter(group_id=group_id).select_related('group').prefetch_related(
                'attachments', 'comments__replies__replies__replies'
            ).order_by('-created_at')
        else:
            return Post._default_manager.filter(group__is_private=False).select_related('group').prefetch_related(
                'attachments', 'comments__replies__replies__replies'
            ).order_by('-created_at')

    def post(self, request):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data.copy()
        data['user_id'] = request.user_id

        if 'group_id' not in data:
            return Response({'error': 'group_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PostSerializer(data=data)
        if serializer.is_valid():
            group_id = serializer.validated_data.get('group_id')
            if group_id:
                try:
                    group = Group._default_manager.get(id=group_id)
                    if not group.can_post(request.user_id):
                        return Response({'error': 'You cannot post in this community'}, status=status.HTTP_403_FORBIDDEN)

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
        try:
            post = Post._default_manager.select_related('group').prefetch_related(
                'attachments', 'comments__replies__replies__replies'
            ).get(id=post_id)

            if post.group.is_private:
                if not hasattr(request, 'user_id') or not request.user_id:
                    return Response({'error': 'Authentication required for private groups'}, status=status.HTTP_401_UNAUTHORIZED)
                if not post.group.can_view(request.user_id):
                    return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

            serializer = PostSerializer(post)
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, post_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            post = Post._default_manager.get(id=post_id, user_id=request.user_id)
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
            post = Post._default_manager.get(id=post_id, user_id=request.user_id)
            post.delete()
            return Response({'message': 'Post deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)


class CommentCreateView(generics.CreateAPIView):
    queryset = Comment._default_manager.all()
    serializer_class = CommentSerializer
    permission_classes = [CommunityPermission]

    def get_permissions(self):
        try:
            post = get_object_or_404(Post, pk=self.kwargs["post_id"])
            if not post.group.is_private:
                from rest_framework.permissions import AllowAny
                return [AllowAny()]
        except:
            pass

        return super().get_permissions()

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
            user_id=self.request.data.get('user_id'),
            user_name=self.request.data.get('user_name', getattr(self.request, 'user_name', f"User {self.request.data.get('user_id')}")),
            email=self.request.data.get('email', getattr(self.request, 'user_email', None)),
            avatar_url=self.request.data.get('user_avatar', getattr(self.request, 'avatar_url', None)),
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
    queryset = Comment._default_manager.all()
    serializer_class = CommentSerializer
    permission_classes = [CommunityPermission]

    def get_permissions(self):
        try:
            post_id = self.kwargs.get('post_id')
            post = Post._default_manager.get(id=post_id)
            if not post.group.is_private:
                from rest_framework.permissions import AllowAny
                return [AllowAny()]
        except:
            pass
        return super().get_permissions()

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
            post = Post._default_manager.get(id=post_id)
            like, created = PostLike._default_manager.get_or_create(
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
            post = Post._default_manager.get(id=post_id)
            like = PostLike._default_manager.get(post=post, user_id=request.user_id)
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
            post = Post._default_manager.get(id=pk)
            like, created = PostLike._default_manager.get_or_create(
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


class CommentLikeToggleView(APIView):
    """Toggle like status for a comment"""

    def post(self, request, comment_id):
        if not hasattr(request, 'user_id') or not request.user_id:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            comment = Comment._default_manager.get(id=comment_id)
            like, created = CommentLike._default_manager.get_or_create(
                comment=comment,
                user_id=request.user_id
            )

            if created:
                comment.like_count = F('like_count') + 1
                comment.save()
                comment.refresh_from_db()
                return Response({
                    "status": "liked",
                    "like_count": comment.like_count,
                    "is_liked": True
                }, status=status.HTTP_200_OK)
            else:
                like.delete()
                comment.like_count = F('like_count') - 1
                comment.save()
                comment.refresh_from_db()
                return Response({
                    "status": "unliked",
                    "like_count": comment.like_count,
                    "is_liked": False
                }, status=status.HTTP_200_OK)

        except Comment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)


class RecommendationMetricsView(APIView):
    """View for getting recommendation system metrics."""

    def get(self, request):
        """Get recommendation system metrics."""
        try:
            system_metrics = metrics_service.get_system_metrics()
            performance_metrics = metrics_service.get_performance_metrics()
            content_metrics = metrics_service.get_content_metrics()

            user_id = request.query_params.get('user_id')
            user_metrics = None
            if user_id:
                user_metrics = metrics_service.get_user_metrics(user_id)

            response_data = {
                'system_metrics': system_metrics,
                'performance_metrics': performance_metrics,
                'content_metrics': content_metrics,
                'timestamp': timezone.now().isoformat()
            }

            if user_metrics:
                response_data['user_metrics'] = user_metrics

            return Response(response_data)

        except Exception as e:
            return Response(
                {'error': f'Error retrieving metrics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )