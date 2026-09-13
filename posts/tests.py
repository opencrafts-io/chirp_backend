from unittest.mock import patch
import uuid
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from rest_framework import status
from rest_framework.test import APITestCase


from communities.models import CommunityMembership
from interactions.models import Block
from .models import Poll, PollOption, PollVote, Post, Community, PostVotes, User


class PostCreateTest(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.author = User.objects.create(
            name="Test User",
            username="testwriter",
            email="test@example.com",
        )

        cls.community = Community.objects.create(
            name="General", visibility="public", private=False, creator=cls.author
        )

        cls.auth_headers = {"HTTP_AUTHORIZATION": "Bearer some-random-jwt"}

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_post_create_view(self, mock_verify):
        mock_verify.return_value = {
            "sub": self.author.user_id,
            "name": self.author.name,
        }

        url = reverse("post-create")
        payload = {
            "title": "Pure positivity",
            "content": "What the title says",
            "author_id": f"{self.author.user_id}",
            "community_id": f"{self.community.id}",
        }

        response = self.client.post(
            url,
            payload,
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


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


class RecordPostViewerViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.author = User.objects.create(
            name="Test User",
            username="testwriter",
            email="test@example.com",
        )

        cls.community = Community.objects.create(
            name="General", visibility="public", private=False, creator=cls.author
        )

        cls.post = Post.objects.create(
            title="Old Legend",
            author=cls.author,
            community=cls.community,
        )

        cls.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer some-random-jwt"}

        cls.url = reverse("record-post-as-viewed", kwargs={"id": cls.post.id})

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_record_view_success(self, mock_verify):
        mock_verify.return_value = {
            "sub": self.author.user_id,
            "name": self.author.name,
        }

        url = reverse("record-post-as-viewed", kwargs={"id": self.post.id})
        payload = {
            "post_id": self.post.id,
            "viewer_id": self.author.user_id,
        }

        response = self.client.post(
            url,
            payload,
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_record_view_idempotency(self, mock_verify):
        mock_verify.return_value = {
            "sub": self.author.user_id,
            "name": self.author.name,
        }

        url = reverse("record-post-as-viewed", kwargs={"id": self.post.id})
        payload = {
            "post_id": self.post.id,
            "viewer_id": self.author.user_id,
        }

        first_response = self.client.post(
            url,
            payload,
            **self.auth_headers,
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.views_count, 1)

        second_response = self.client.post(
            url,
            payload,
            **self.auth_headers,
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.views_count, 1)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_record_view_from_non_existent_user(self, mock_verify):
        random_uuid = uuid.uuid4()
        mock_verify.return_value = {
            "sub": self.author.user_id,
            "name": self.author.name,
        }

        url = reverse("record-post-as-viewed", kwargs={"id": self.post.id})
        payload = {
            "post_id": self.post.id,
            "viewer_id": random_uuid,
        }
        response = self.client.post(
            url,
            payload,
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.post.refresh_from_db()
        self.assertEqual(self.post.views_count, 0)


class PostVotesTest(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.author = User.objects.create(
            name="Test User",
            username="testwriter",
            email="test@example.com",
        )

        cls.community = Community.objects.create(
            name="General", visibility="public", private=False, creator=cls.author
        )

        cls.post = Post.objects.create(
            title="Old Legend",
            author=cls.author,
            community=cls.community,
        )

        cls.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer some-random-jwt"}

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_record_vote_success(self, mock_verify):
        mock_verify.return_value = {
            "sub": self.author.user_id,
            "name": self.author.name,
        }

        url = reverse("post-vote", kwargs={"post_id": self.post.id})
        payload = {
            "post_id": self.post.id,
            "voter_id": self.author.user_id,
            "value": 1,  # For upvote
        }
        response = self.client.post(
            url,
            payload,
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 201)

        self.post.refresh_from_db()
        self.assertEqual(self.post.upvotes, 1)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_view_vote_success(self, mock_verify):
        mock_verify.return_value = {
            "sub": self.author.user_id,
            "name": self.author.name,
        }

        PostVotes.objects.update_or_create(
            post=self.post,
            user=self.author,
            defaults={"value": 1},
        )

        url = reverse("post-vote", kwargs={"post_id": self.post.id})
        response = self.client.get(
            url,
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["value"], 1)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_downvote_after_upvote_success(self, mock_verify):
        mock_verify.return_value = {
            "sub": self.author.user_id,
            "name": self.author.name,
        }

        url = reverse("post-vote", kwargs={"post_id": self.post.id})
        payload = {
            "post_id": self.post.id,
            "voter_id": self.author.user_id,
            "value": 1,
        }
        response = self.client.post(
            url,
            payload,
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["value"], 1)
        self.post.refresh_from_db()
        self.assertEqual(self.post.upvotes, 1, "Post votes should be equal to one.")

        url = reverse("post-vote", kwargs={"post_id": self.post.id})
        payload = {
            "post_id": self.post.id,
            "voter_id": self.author.user_id,
            "value": -1,
        }
        response = self.client.post(
            url,
            payload,
            **self.auth_headers,
        )

        print(response.json())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["value"], -1)
        self.post.refresh_from_db()
        self.assertEqual(self.post.upvotes, 0, "Post votes should be equal to zero.")


class PollTests(APITestCase):
    """
    Covers docs: create-with-poll validation, vote/retract semantics,
    per-user `my_votes`, and the voters listing (incl. anonymous gating).
    """

    @classmethod
    def setUpTestData(cls) -> None:
        cls.author = User.objects.create(
            name="Poll Author", username="pollster", email="author@example.com"
        )
        cls.voter = User.objects.create(
            name="Voter", username="voter", email="voter@example.com"
        )
        cls.community = Community.objects.create(
            name="General", visibility="public", private=False, creator=cls.author
        )
        for user in (cls.author, cls.voter):
            CommunityMembership.objects.get_or_create(
                community=cls.community, user=user, defaults={"role": "member"}
            )
        cls.auth_headers = {"HTTP_AUTHORIZATION": "Bearer some-random-jwt"}

    # ---- helpers -----------------------------------------------------------

    def _as(self, mock_verify, user):
        mock_verify.return_value = {"sub": user.user_id, "name": user.name}

    def _create_post(self, poll=None, **overrides):
        payload = {
            "title": "Which unit first?",
            "content": "Vote below",
            "author_id": str(self.author.user_id),
            "community_id": self.community.id,
        }
        if poll is not None:
            payload["poll"] = poll
        payload.update(overrides)
        return self.client.post(
            reverse("post-create"), payload, format="json", **self.auth_headers
        )

    def _make_poll(self, allows_multiple=False, is_anonymous=False, ends_at=None):
        post = Post.objects.create(
            title="t", content="c", author=self.author, community=self.community
        )
        poll = Poll.objects.create(
            post=post,
            question="Which unit first?",
            allows_multiple=allows_multiple,
            is_anonymous=is_anonymous,
            ends_at=ends_at,
        )
        options = [
            PollOption.objects.create(poll=poll, text=t, position=i)
            for i, t in enumerate(["Calculus", "Databases", "Networks"])
        ]
        return poll, options

    def _vote(self, poll, option_ids):
        return self.client.post(
            reverse("poll-vote", kwargs={"poll_id": poll.id}),
            {"option_ids": option_ids},
            format="json",
            **self.auth_headers,
        )

    def _retract(self, poll):
        return self.client.delete(
            reverse("poll-vote", kwargs={"poll_id": poll.id}),
            format="json",
            **self.auth_headers,
        )

    @staticmethod
    def _counts(poll_json):
        return [o["vote_count"] for o in poll_json["options"]]

    # ---- creation ----------------------------------------------------------

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_create_post_with_poll(self, mock_verify):
        self._as(mock_verify, self.author)
        ends_at = timezone.now() + timedelta(days=2)
        response = self._create_post(
            poll={
                "question": "  Which unit first?  ",
                "allows_multiple": True,
                "is_anonymous": False,
                "ends_at": ends_at.isoformat(),
                # Positions deliberately out of order / sparse.
                "options": [
                    {"text": "Databases", "position": 5},
                    {"text": "Calculus", "position": 1},
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        poll = response.data["poll"]
        self.assertEqual(poll["question"], "Which unit first?")
        self.assertTrue(poll["allows_multiple"])
        self.assertEqual(poll["post"], response.data["id"])
        self.assertEqual(poll["total_votes"], 0)
        self.assertEqual(poll["my_votes"], [])
        self.assertEqual(
            [(o["text"], o["position"]) for o in poll["options"]],
            [("Calculus", 0), ("Databases", 1)],
        )
        self.assertTrue(all(o["id"] for o in poll["options"]))
        self.assertEqual(Poll.objects.count(), 1)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_create_post_without_poll_is_unchanged(self, mock_verify):
        self._as(mock_verify, self.author)
        response = self._create_post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["poll"])

        # An explicit null is accepted too.
        response = self.client.post(
            reverse("post-create"),
            {
                "title": "No poll",
                "content": "c",
                "author_id": str(self.author.user_id),
                "community_id": self.community.id,
                "poll": None,
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data["poll"])

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_create_post_poll_validation(self, mock_verify):
        self._as(mock_verify, self.author)
        base = {"question": "Which unit first?"}
        two = [{"text": "A"}, {"text": "B"}]
        cases = {
            "one option": {**base, "options": [{"text": "A"}]},
            "eleven options": {
                **base,
                "options": [{"text": f"O{i}"} for i in range(11)],
            },
            "duplicate (case/space)": {
                **base,
                "options": [{"text": "Calc"}, {"text": " calc "}],
            },
            "empty option": {**base, "options": [{"text": "A"}, {"text": "  "}]},
            "short question": {"question": "Hi", "options": two},
            "long question": {"question": "x" * 201, "options": two},
            "long option": {**base, "options": [{"text": "x" * 101}, {"text": "B"}]},
            "ends_at in the past": {
                **base,
                "options": two,
                "ends_at": (timezone.now() - timedelta(minutes=1)).isoformat(),
            },
            "ends_at too soon": {
                **base,
                "options": two,
                "ends_at": (timezone.now() + timedelta(minutes=2)).isoformat(),
            },
        }
        for name, poll in cases.items():
            with self.subTest(name):
                response = self._create_post(poll=poll)
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.data
                )
                self.assertIn("poll", response.data)
        self.assertEqual(Post.objects.count(), 0)

    # ---- voting ------------------------------------------------------------

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_single_choice_vote_replace_and_errors(self, mock_verify):
        self._as(mock_verify, self.voter)
        poll, (a, b, _) = self._make_poll()

        response = self._vote(poll, [a.id])
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["my_votes"], [a.id])
        self.assertEqual(response.data["total_votes"], 1)
        self.assertEqual(self._counts(response.data), [1, 0, 0])

        # Switching replaces the previous choice; the voter is still counted once.
        response = self._vote(poll, [b.id])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["my_votes"], [b.id])
        self.assertEqual(response.data["total_votes"], 1)
        self.assertEqual(self._counts(response.data), [0, 1, 0])
        self.assertEqual(PollVote.objects.filter(poll=poll).count(), 1)

        # Denormalized columns match the rows.
        poll.refresh_from_db()
        self.assertEqual(poll.total_votes, 1)
        self.assertEqual(
            list(poll.options.values_list("vote_count", flat=True)), [0, 1, 0]
        )

        for name, ids in {
            "two ids on single choice": [a.id, b.id],
            "unknown id": [999999],
            "empty": [],
        }.items():
            with self.subTest(name):
                response = self._vote(poll, ids)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Failed attempts must not disturb the existing selection.
        poll.refresh_from_db()
        self.assertEqual(poll.total_votes, 1)

        response = self._vote(Poll(id=424242), [a.id])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_multi_choice_vote_and_retract(self, mock_verify):
        self._as(mock_verify, self.voter)
        poll, (a, b, c) = self._make_poll(allows_multiple=True)

        response = self._vote(poll, [c.id, a.id, a.id])
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["my_votes"], [a.id, c.id])  # by position
        self.assertEqual(response.data["total_votes"], 1)  # one voter
        self.assertEqual(self._counts(response.data), [1, 0, 1])

        # The prefetched feed path orders my_votes the same way.
        feed = self.client.get(reverse("post-feed"), **self.auth_headers)
        self.assertEqual(feed.data["results"][0]["poll"]["my_votes"], [a.id, c.id])

        response = self._retract(poll)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["my_votes"], [])
        self.assertEqual(response.data["total_votes"], 0)
        self.assertEqual(self._counts(response.data), [0, 0, 0])

        # Retracting again is a no-op, not an error.
        response = self._retract(poll)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_votes"], 0)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_total_votes_counts_distinct_voters(self, mock_verify):
        poll, (a, b, _) = self._make_poll(allows_multiple=True)
        self._as(mock_verify, self.voter)
        self._vote(poll, [a.id, b.id])
        self._as(mock_verify, self.author)
        response = self._vote(poll, [a.id])
        self.assertEqual(response.data["total_votes"], 2)
        self.assertEqual(self._counts(response.data), [2, 1, 0])
        self.assertEqual(response.data["my_votes"], [a.id])

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_closed_poll_rejects_votes(self, mock_verify):
        self._as(mock_verify, self.voter)
        poll, (a, _, _) = self._make_poll(
            ends_at=timezone.now() - timedelta(minutes=1)
        )
        response = self._vote(poll, [a.id])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PollVote.objects.count(), 0)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_closed_poll_rejects_retraction(self, mock_verify):
        """Final results stay final: a vote cast before close can't be pulled."""
        self._as(mock_verify, self.voter)
        poll, (a, _, _) = self._make_poll()
        self._vote(poll, [a.id])
        Poll.objects.filter(id=poll.id).update(
            ends_at=timezone.now() - timedelta(minutes=1)
        )
        response = self._retract(poll)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        poll.refresh_from_db()
        self.assertEqual(poll.total_votes, 1)

    # ---- access ------------------------------------------------------------

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_private_community_poll_requires_membership(self, mock_verify):
        outsider = User.objects.create(name="Out", username="out", email="o@x.io")
        private = Community.objects.create(
            name="Secret", visibility="private", private=True, creator=self.author
        )
        CommunityMembership.objects.get_or_create(
            community=private, user=self.author, defaults={"role": "member"}
        )
        post = Post.objects.create(title="t", author=self.author, community=private)
        poll = Poll.objects.create(post=post, question="Members only?")
        a = PollOption.objects.create(poll=poll, text="Yes", position=0)
        b = PollOption.objects.create(poll=poll, text="No", position=1)

        self._as(mock_verify, outsider)
        self.assertEqual(self._vote(poll, [a.id]).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self._retract(poll).status_code, status.HTTP_403_FORBIDDEN)
        voters = self.client.get(
            reverse("poll-voters", kwargs={"poll_id": poll.id}), **self.auth_headers
        )
        self.assertEqual(voters.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(PollVote.objects.count(), 0)

        # A member of the private community can vote as usual.
        self._as(mock_verify, self.author)
        self.assertEqual(self._vote(poll, [b.id]).status_code, status.HTTP_200_OK)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_banned_member_cannot_vote_or_list_voters(self, mock_verify):
        poll, (a, _, _) = self._make_poll()
        CommunityMembership.objects.filter(
            community=self.community, user=self.voter
        ).update(banned=True)
        self._as(mock_verify, self.voter)
        self.assertEqual(self._vote(poll, [a.id]).status_code, status.HTTP_403_FORBIDDEN)
        voters = self.client.get(
            reverse("poll-voters", kwargs={"poll_id": poll.id}), **self.auth_headers
        )
        self.assertEqual(voters.status_code, status.HTTP_403_FORBIDDEN)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_blocked_users_cannot_interact_with_each_others_polls(self, mock_verify):
        poll, (a, _, _) = self._make_poll()  # authored by self.author
        Block.objects.create(
            blocker=self.author, blocked_user=self.voter, block_type="user"
        )
        self._as(mock_verify, self.voter)
        self.assertEqual(self._vote(poll, [a.id]).status_code, status.HTTP_403_FORBIDDEN)

    # ---- reads -------------------------------------------------------------

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_feed_and_detail_embed_poll_with_requesters_votes(self, mock_verify):
        poll, (a, b, _) = self._make_poll()
        self._as(mock_verify, self.voter)
        self._vote(poll, [a.id])
        self._as(mock_verify, self.author)
        self._vote(poll, [b.id])

        # Author's view
        response = self.client.get(reverse("post-feed"), **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        feed_poll = response.data["results"][0]["poll"]
        self.assertEqual(feed_poll["id"], poll.id)
        self.assertEqual(feed_poll["my_votes"], [b.id])
        self.assertEqual(feed_poll["total_votes"], 2)

        detail = self.client.get(
            reverse("get-post-by-id", kwargs={"id": poll.post_id}), **self.auth_headers
        )
        self.assertEqual(detail.data["poll"]["my_votes"], [b.id])

        # Voter's view of the same post
        self._as(mock_verify, self.voter)
        detail = self.client.get(
            reverse("get-post-by-id", kwargs={"id": poll.post_id}), **self.auth_headers
        )
        self.assertEqual(detail.data["poll"]["my_votes"], [a.id])

        community = self.client.get(
            reverse("get-post-by-community", kwargs={"community_id": self.community.id}),
            **self.auth_headers,
        )
        self.assertEqual(community.data["results"][0]["poll"]["my_votes"], [a.id])

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_feed_poll_queries_do_not_scale_with_posts(self, mock_verify):
        self._as(mock_verify, self.voter)
        for _ in range(6):
            poll, (a, _, _) = self._make_poll()
            self._vote(poll, [a.id])

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("post-feed"), **self.auth_headers)
        self.assertEqual(len(response.data["results"]), 6)
        self.assertTrue(all(p["poll"]["my_votes"] for p in response.data["results"]))

        # One query for options, one for the requester's votes — regardless of
        # how many posts are on the page.
        poll_queries = [q["sql"] for q in ctx.captured_queries]
        self.assertEqual(
            len([q for q in poll_queries if 'FROM "posts_polloption"' in q]), 1
        )
        self.assertEqual(
            len([q for q in poll_queries if 'FROM "posts_pollvote"' in q]), 1
        )

    # ---- voters ------------------------------------------------------------

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_voters_listing_filters_and_paginates(self, mock_verify):
        poll, (a, b, _) = self._make_poll(allows_multiple=True)
        self._as(mock_verify, self.voter)
        self._vote(poll, [a.id, b.id])
        self._as(mock_verify, self.author)
        self._vote(poll, [b.id])

        url = reverse("poll-voters", kwargs={"poll_id": poll.id})
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["count"], 2)
        rows = {str(r["user_id"]): r for r in response.data["results"]}
        self.assertEqual(rows[str(self.voter.user_id)]["option_ids"], [a.id, b.id])
        self.assertEqual(rows[str(self.author.user_id)]["option_ids"], [b.id])
        self.assertEqual(rows[str(self.voter.user_id)]["user"]["username"], "voter")
        self.assertTrue(all(r["voted_at"] for r in response.data["results"]))
        # Most recent voter first.
        self.assertEqual(
            str(response.data["results"][0]["user_id"]), str(self.author.user_id)
        )

        response = self.client.get(url, {"option_id": a.id}, **self.auth_headers)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            str(response.data["results"][0]["user_id"]), str(self.voter.user_id)
        )

        response = self.client.get(url, {"page_size": 1}, **self.auth_headers)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])

        response = self.client.get(url, {"option_id": "x"}, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("chirp.verisafe_authentication.verify_verisafe_jwt")
    def test_anonymous_poll_voters_only_visible_to_author(self, mock_verify):
        poll, (a, _, _) = self._make_poll(is_anonymous=True)
        self._as(mock_verify, self.voter)
        self._vote(poll, [a.id])
        url = reverse("poll-voters", kwargs={"poll_id": poll.id})

        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self._as(mock_verify, self.author)
        response = self.client.get(url, **self.auth_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_recount_after_option_removed(self):
        """Removing an option (e.g. via the admin inline) must re-derive totals."""
        poll, (a, b, _) = self._make_poll(allows_multiple=True)
        PollVote.objects.create(poll=poll, option=a, user=self.voter)
        PollVote.objects.create(poll=poll, option=b, user=self.voter)
        PollVote.objects.create(poll=poll, option=a, user=self.author)
        poll.recount()
        self.assertEqual(poll.total_votes, 2)

        a.delete()  # cascades the two votes on option A
        poll.recount()
        poll.refresh_from_db()
        self.assertEqual(poll.total_votes, 1)  # only the voter still has a vote
        self.assertEqual(list(poll.options.values_list("vote_count", flat=True)), [1, 0])

    def test_deleting_post_cascades_poll(self):
        poll, _ = self._make_poll()
        PollVote.objects.create(poll=poll, option=poll.options.first(), user=self.voter)
        poll.post.delete()
        self.assertEqual(Poll.objects.count(), 0)
        self.assertEqual(PollOption.objects.count(), 0)
        self.assertEqual(PollVote.objects.count(), 0)
