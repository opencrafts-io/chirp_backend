from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Attachment, Post, PostLike, PostReply
from .serializers import PostReplySerializer, PostSerializer
from .permissions import IsAuthenticatedCustom
from django.db.models import Exists, F, OuterRef


class PostCreateView(generics.CreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedCustom]

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
            attachment_type = "image" if "image" in file.content_type else "file"
            Attachment.objects.create(
                post=post, file=file, attachment_type=attachment_type
            )

        response_serializer = self.get_serializer(post)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class PostListView(generics.ListAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        user_id = self.request.user_id
        queryset = Post.objects.all().order_by("-created_at")

        if user_id:
            user_likes = PostLike.objects.filter(
                user_id=user_id, post_id=OuterRef("pk")
            )
            queryset = queryset.annotate(is_liked=Exists(user_likes))

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user_id"] = self.request.user_id
        return context


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedCustom]

    def get_queryset(self):
        user_id = self.request.user_id
        queryset = Post.objects.all()

        if user_id:
            user_likes = PostLike.objects.filter(
                user_id=user_id, post_id=OuterRef("pk")
            )
            queryset = queryset.annotate(is_liked=Exists(user_likes))

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user_id"] = self.request.user_id
        return context


class PostReplyCreateView(generics.CreateAPIView):
    queryset = PostReply.objects.all()
    serializer_class = PostReplySerializer
    permission_classes = [IsAuthenticatedCustom]

    def perform_create(self, serializer):
        parent_post = get_object_or_404(Post, pk=self.kwargs["post_id"])
        serializer.save(user_id=self.request.user_id, parent_post=parent_post)


class PostLikeToggleView(APIView):
    permission_classes = [IsAuthenticatedCustom]

    def post(self, request, pk, format=None):
        post = get_object_or_404(Post, pk=pk)
        user_id = request.user_id

        like, created = PostLike.objects.get_or_create(user_id=user_id, post=post)

        if created:
            Post.objects.filter(pk=pk).update(like_count=F("like_count") + 1)
            return Response({"status": "liked"}, status=status.HTTP_201_CREATED)

        return Response({"status": "already liked"}, status=status.HTTP_200_OK)

    def delete(self, request, pk, format=None):
        post = get_object_or_404(Post, pk=pk)
        user_id = request.user_id

        deleted_count, _ = PostLike.objects.filter(user_id=user_id, post=post).delete()

        if deleted_count > 0:
            Post.objects.filter(pk=pk).update(like_count=F("like_count") - 1)
            return Response({"status": "unliked"}, status=status.HTTP_204_NO_CONTENT)

        return Response({"status": "not liked"}, status=status.HTTP_404_NOT_FOUND)