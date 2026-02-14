from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from .models import Post, Community, User


class PostRankingTest(TestCase):
    def setUp(self):
        """
        Create the necessary environment for every test case.
        """
        # 1. Create a User (Primary Key is a UUID)
        self.author = User.objects.create(
            name="Test User", username="testwriter", email="test@example.com"
        )

        # 2. Create a Community
        # We need this because Post.community is a required ForeignKey
        self.community = Community.objects.create(
            name="General", visibility="public", private=False, creator=self.author
        )

    def test_hot_ranking_logic(self):
        """
        Verify that the 'hot_score' correctly prioritizes
        new engagement over old massive popularity.
        """
        # Scenario A: The "Old Legend"
        # High upvotes (1000), but 10 days old.
        old_legend = Post.objects.create(
            title="Old Legend",
            author=self.author,
            community=self.community,
            upvotes=1000,
        )
        old_date = timezone.now() - timedelta(days=10)
        Post.objects.filter(pk=old_legend.pk).update(created_at=old_date)

        # Scenario B: The "Rising Star"
        # Moderate upvotes (50), but only 1 hour old.
        rising_star = Post.objects.create(
            title="Rising Star",
            author=self.author,
            community=self.community,
            upvotes=50,
        )
        new_date = timezone.now() - timedelta(hours=1)
        Post.objects.filter(pk=rising_star.pk).update(created_at=new_date)

        # Fetch using our modular .hot() manager method
        feed = Post.objects.hot()

        # Assertions
        # In a healthy feed, the Rising Star should beat the Old Legend
        self.assertEqual(feed[0], rising_star, "New content should be at the top.")
        self.assertEqual(feed[1], old_legend, "Old content should decay.")

        # Verify the actual scores exist and are ordered
        self.assertGreater(feed[0].hot_score, feed[1].hot_score)

    def test_controversial_content_sinks(self):
        """
        Tests that downvotes effectively lower the ranking
        even if upvote counts are high.
        """
        # Post with 20 upvotes and 0 downvotes
        positive_post = Post.objects.create(
            title="Pure Positivity",
            author=self.author,
            community=self.community,
            upvotes=20,
        )

        # Post with 30 upvotes but 40 downvotes
        controversial_post = Post.objects.create(
            title="Arguments Everywhere",
            author=self.author,
            community=self.community,
            upvotes=30,
            downvotes=40,
        )

        feed = Post.objects.hot()

        # The post with fewer net points should be lower
        self.assertEqual(feed[0], positive_post)
