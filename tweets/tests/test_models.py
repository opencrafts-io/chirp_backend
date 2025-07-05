from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from ..models import Tweets


class TweetsModelTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.valid_tweet_data = {
            'user_id': 'user123',
            'content': 'This is a test tweet!'
        }

    def test_create_valid_tweet(self):
        """Test creating a valid tweet with all required fields."""
        tweet = Tweets.objects.create(**self.valid_tweet_data)
        self.assertEqual(tweet.user_id, 'user123')
        self.assertEqual(tweet.content, 'This is a test tweet!')
        self.assertIsNotNone(tweet.created_at)
        self.assertIsNotNone(tweet.updated_at)
        self.assertIsNotNone(tweet.id)

    def test_tweet_string_representation(self):
        """Test the __str__ method returns expected format."""
        tweet = Tweets.objects.create(**self.valid_tweet_data)
        expected_str = f"{tweet.user_id}: {tweet.content}..."
        self.assertEqual(str(tweet), expected_str)

    def test_tweet_content_max_length(self):
        """Test tweet content respects 280 character limit."""
        long_content = 'x' * 281  # 281 characters
        tweet_data = self.valid_tweet_data.copy()
        tweet_data['content'] = long_content

        tweet = Tweets(**tweet_data)
        with self.assertRaises(ValidationError):
            tweet.full_clean()

    def test_tweet_content_at_max_length(self):
        """Test tweet content works at exactly 280 characters."""
        max_content = 'x' * 280  # Exactly 280 characters
        tweet_data = self.valid_tweet_data.copy()
        tweet_data['content'] = max_content

        tweet = Tweets.objects.create(**tweet_data)
        self.assertEqual(len(tweet.content), 280)

    def test_tweet_user_id_max_length(self):
        """Test user_id respects 100 character limit."""
        long_user_id = 'x' * 101  # 101 characters
        tweet_data = self.valid_tweet_data.copy()
        tweet_data['user_id'] = long_user_id

        tweet = Tweets(**tweet_data)
        with self.assertRaises(ValidationError):
            tweet.full_clean()

    def test_tweet_empty_content(self):
        """Test that empty content is not allowed."""
        tweet_data = self.valid_tweet_data.copy()
        tweet_data['content'] = ''

        tweet = Tweets(**tweet_data)
        with self.assertRaises(ValidationError):
            tweet.full_clean()

    def test_tweet_empty_user_id(self):
        """Test that empty user_id is not allowed."""
        tweet_data = self.valid_tweet_data.copy()
        tweet_data['user_id'] = ''

        tweet = Tweets(**tweet_data)
        with self.assertRaises(ValidationError):
            tweet.full_clean()

    def test_tweet_auto_timestamps(self):
        """Test that created_at and updated_at are automatically set."""
        tweet = Tweets.objects.create(**self.valid_tweet_data)
        self.assertIsNotNone(tweet.created_at)
        self.assertIsNotNone(tweet.updated_at)

    def test_tweet_updated_at_changes(self):
        """Test that updated_at changes when tweet is modified."""
        tweet = Tweets.objects.create(**self.valid_tweet_data)
        original_updated_at = tweet.updated_at

        tweet.content = 'Updated content'
        tweet.save()

        self.assertNotEqual(tweet.updated_at, original_updated_at)

    def test_multiple_tweets_same_user(self):
        """Test that same user can create multiple tweets."""
        tweet1 = Tweets.objects.create(**self.valid_tweet_data)
        tweet2_data = self.valid_tweet_data.copy()
        tweet2_data['content'] = 'Second tweet'
        tweet2 = Tweets.objects.create(**tweet2_data)

        self.assertEqual(tweet1.user_id, tweet2.user_id)
        self.assertNotEqual(tweet1.content, tweet2.content)
        self.assertNotEqual(tweet1.id, tweet2.id)

    def test_tweet_ordering(self):
        """Test default ordering (if any) of tweets."""
        tweet1 = Tweets.objects.create(**self.valid_tweet_data)
        tweet2_data = self.valid_tweet_data.copy()
        tweet2_data['content'] = 'Second tweet'
        tweet2 = Tweets.objects.create(**tweet2_data)

        tweets = Tweets.objects.all()
        self.assertEqual(tweets.count(), 2)
        # Verify both tweets are retrieved
        self.assertIn(tweet1, tweets)
        self.assertIn(tweet2, tweets)