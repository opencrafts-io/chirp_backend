from django.test import TestCase
from rest_framework.test import APIRequestFactory
from ..models import Tweets
from ..serializers import StatusSerializer


class StatusSerializerTest(TestCase):
    def setUp(self):
        """Set up test data for each test method."""
        self.factory = APIRequestFactory()
        self.valid_tweet_data = {
            'user_id': 'user123',
            'content': 'This is a test tweet!'
        }
        self.valid_serializer_data = {
            'content': 'This is a test tweet!'
        }

    def test_serializer_valid_data(self):
        """Test serializer with valid data."""
        serializer = StatusSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['content'], 'This is a test tweet!')

    def test_serializer_save_creates_tweet(self):
        """Test that serializer save creates a tweet object."""
        serializer = StatusSerializer(data=self.valid_serializer_data)
        self.assertTrue(serializer.is_valid())

        # Mock user_id assignment (normally done in view)
        serializer.validated_data['user_id'] = 'user123'
        tweet = serializer.save()

        self.assertIsInstance(tweet, Tweets)
        self.assertEqual(tweet.content, 'This is a test tweet!')
        self.assertEqual(tweet.user_id, 'user123')

    def test_serializer_read_only_fields(self):
        """Test that read-only fields cannot be set during creation."""
        data_with_readonly = self.valid_serializer_data.copy()
        data_with_readonly.update({
            'id': 999,
            'user_id': 'hacker123',
            'created_at': '2023-01-01T00:00:00Z',
            'updated_at': '2023-01-01T00:00:00Z'
        })

        serializer = StatusSerializer(data=data_with_readonly)
        self.assertTrue(serializer.is_valid())

        # Check that read-only fields are not in validated_data
        self.assertNotIn('id', serializer.validated_data)
        self.assertNotIn('user_id', serializer.validated_data)
        self.assertNotIn('created_at', serializer.validated_data)
        self.assertNotIn('updated_at', serializer.validated_data)

    def test_serializer_empty_content(self):
        """Test serializer with empty content."""
        data = {'content': ''}
        serializer = StatusSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

    def test_serializer_missing_content(self):
        """Test serializer with missing content field."""
        data = {}
        serializer = StatusSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

    def test_serializer_content_too_long(self):
        """Test serializer with content exceeding 280 characters."""
        data = {'content': 'x' * 281}
        serializer = StatusSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('content', serializer.errors)

    def test_serializer_content_at_max_length(self):
        """Test serializer with content at exactly 280 characters."""
        data = {'content': 'x' * 280}
        serializer = StatusSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_to_representation(self):
        """Test serializer converts model instance to dict representation."""
        tweet = Tweets.objects.create(**self.valid_tweet_data)
        serializer = StatusSerializer(tweet)

        expected_fields = ['id', 'user_id', 'content', 'created_at', 'updated_at']
        for field in expected_fields:
            self.assertIn(field, serializer.data)

        self.assertEqual(serializer.data['content'], 'This is a test tweet!')
        self.assertEqual(serializer.data['user_id'], 'user123')

    def test_serializer_many_tweets(self):
        """Test serializer with many=True for multiple tweets."""
        tweet1 = Tweets.objects.create(**self.valid_tweet_data)
        tweet2_data = self.valid_tweet_data.copy()
        tweet2_data['content'] = 'Second tweet'
        tweet2 = Tweets.objects.create(**tweet2_data)

        tweets = [tweet1, tweet2]
        serializer = StatusSerializer(tweets, many=True)

        self.assertEqual(len(serializer.data), 2)
        self.assertEqual(serializer.data[0]['content'], 'This is a test tweet!')
        self.assertEqual(serializer.data[1]['content'], 'Second tweet')

    def test_serializer_partial_update(self):
        """Test serializer with partial update (patch)."""
        tweet = Tweets.objects.create(**self.valid_tweet_data)
        update_data = {'content': 'Updated content'}

        serializer = StatusSerializer(tweet, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated_tweet = serializer.save()
        self.assertEqual(updated_tweet.content, 'Updated content')
        self.assertEqual(updated_tweet.user_id, 'user123')  # Should remain unchanged

    def test_serializer_validation_with_whitespace(self):
        """Test serializer handles whitespace-only content."""
        data = {'content': '   \n\t   '}
        serializer = StatusSerializer(data=data)
        # This should be valid as Django's TextField doesn't strip whitespace by default
        # But you might want to add custom validation for this
        self.assertTrue(serializer.is_valid())

    def test_serializer_special_characters(self):
        """Test serializer handles special characters in content."""
        special_content = 'Hello! 🌟 This has émojis and spécial chars: @#$%^&*()'
        data = {'content': special_content}
        serializer = StatusSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Mock user_id assignment
        serializer.validated_data['user_id'] = 'user123'
        tweet = serializer.save()
        self.assertEqual(tweet.content, special_content)