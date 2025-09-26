import uuid
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from ..models import Post, Comment, CommentLike
from groups.models import Group

#
# @override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
# class CommentLikeTest(TestCase):
#     def setUp(self):
#         self.client = APIClient()
#
#         # Create a group first
#         self.group, created = Group.objects.get_or_create(
#             id=1,
#             defaults={
#                 "name": "Test Group",
#                 "description": "Test group",
#                 "creator_id": "test_user",
#                 "creator_name": "Test User",
#             },
#         )
#
#         user_uuid = uuid.uuid4()
#         self.post = Post.objects.create(
#             group=self.group,
#             user_id=user_uuid,
#             user_name="Test User",
#             content="Test post content",
#         )
#         self.comment = Comment.objects.create(
#             post=self.post,
#             user_id=user_uuid,
#             user_name="Comment User",
#             content="Test comment",
#         )
#         self.reply = Comment.objects.create(
#             post=self.post,
#             parent_comment=self.comment,
#             user_id=user_uuid,
#             user_name="Reply User",
#             content="Test reply",
#         )
#
#     def test_like_comment(self):
#         """Test liking a comment"""
#         url = reverse("comment-like", kwargs={"comment_id": self.comment.id})
#
#         # Mock authentication by directly calling the view
#         from posts.views import CommentLikeToggleView
#
#         view = CommentLikeToggleView()
#
#         # Create a mock request
#         from django.test import RequestFactory
#
#         factory = RequestFactory()
#         request = factory.post(url)
#         request.user_id = uuid.uuid4()
#         request.user_name = "Test Liker"
#         request.user_email = "test@example.com"
#
#         response = view.post(request, comment_id=self.comment.id)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["status"], "liked")
#         self.assertEqual(response.data["like_count"], 1)
#         self.assertTrue(response.data["is_liked"])
#
#     def test_unlike_comment(self):
#         """Test unliking a comment"""
#         # First like the comment
#         CommentLike.objects.create(comment=self.comment, user_id=uuid.uuid4())
#         self.comment.like_count = 1
#         self.comment.save()
#
#         url = reverse("comment-like", kwargs={"comment_id": self.comment.id})
#
#         # Mock authentication by directly calling the view
#         from posts.views import CommentLikeToggleView
#
#         view = CommentLikeToggleView()
#
#         # Create a mock request
#         from django.test import RequestFactory
#
#         factory = RequestFactory()
#         request = factory.post(url)
#         request.user_id = uuid.uuid4()
#         request.user_name = "Test Liker"
#         request.user_email = "test@example.com"
#
#         response = view.post(request, comment_id=self.comment.id)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["status"], "unliked")
#         self.assertEqual(response.data["like_count"], 0)
#         self.assertFalse(response.data["is_liked"])
#
#     def test_like_reply(self):
#         """Test liking a reply to a comment"""
#         url = reverse("comment-like", kwargs={"comment_id": self.reply.id})
#
#         # Mock authentication by directly calling the view
#         from posts.views import CommentLikeToggleView
#
#         view = CommentLikeToggleView()
#
#         # Create a mock request
#         from django.test import RequestFactory
#
#         factory = RequestFactory()
#         request = factory.post(url)
#         request.user_id = uuid.uuid4()
#         request.user_name = "Test Liker"
#         request.user_email = "test@example.com"
#
#         response = view.post(request, comment_id=self.reply.id)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["status"], "liked")
#         self.assertEqual(response.data["like_count"], 1)
#         self.assertTrue(response.data["is_liked"])
#
#     def test_comment_serializer_includes_like_info(self):
#         """Test that comment serializer includes like information"""
#         from ..serializers import CommentSerializer
#
#         liker_id = uuid.uuid4()
#         # Create a like
#         CommentLike.objects.create(comment=self.comment, user_id=liker_id)
#         self.comment.like_count = 1
#         self.comment.save()
#
#         # Mock request context
#         class MockRequest:
#             def __init__(self):
#                 self.user_id = liker_id
#
#         serializer = CommentSerializer(self.comment, context={"request": MockRequest()})
#
#         data = serializer.data
#         self.assertEqual(data["like_count"], 1)
#         self.assertTrue(data["is_liker"])
