from django.db import models
from django.db.models import F, FloatField, ExpressionWrapper
from django.db.models.functions import Extract, Now


class PostQuerySet(models.QuerySet):
    def annotate_hot_score(self, gravity=1.8, time_buffer=2.0):
        """
        Calculates a 'hot_score' based on the Hacker News Ranking Algorithm.

        The algorithm balances content quality (votes/engagement) against
        freshness (time elapsed).

        FORMULA: (Points + 1) / (Age_in_Hours + 2)^Gravity

        ALGORITHM BREAKDOWN:
        1. MAGNITUDE (The Numerator):
           We calculate a weighted sum of interactions.
           - Upvotes (x3): Primary quality signal.
           - Downvotes (-x2): Penalty for poor content.
           - Comments (x2): Higher value than views due to active effort.
           - Views (x0.5): Minor 'social proof' nudge.
           - (+1): Ensures the numerator is never zero, allowing new posts
                  with no votes to still have a starting score.

        2. TIME DECAY (The Denominator):
           - Age: Calculated as (Current_Time - Created_Time) in hours.
           - Time Buffer (+2): Prevents 'Division by Zero' errors for brand
             new posts and prevents the score from dropping too drastically
             in the first 60 minutes.
           - Gravity (^1.8): An exponential power that determines how fast
             content 'sinks'. A higher number makes the feed move faster.

        3. RESULT:
           As 'Age' increases, the denominator grows exponentially, eventually
           overpowering even high-vote counts, ensuring a rotating front page.
        """

        # Define the quality weights (The 'Numerator')
        points_expr = (
            (F("upvotes") * 3)
            - (F("downvotes") * 2)
            + (F("comment_count") * 2)
            + (F("views_count") * 0.5)
            + 1
        )

        # Calculate time elapsed in hours (The 'Denominator')
        # ExtractEpoch converts timestamps to total seconds for math operations
        seconds_since_epoch = Extract(Now() - F("created_at"), "epoch")
        age_in_hours = seconds_since_epoch / 3600.0

        # Wrap the math in an ExpressionWrapper to tell Django to expect a Float
        return self.annotate(
            hot_score=ExpressionWrapper(
                points_expr / ((age_in_hours + time_buffer) ** gravity),
                output_field=FloatField(),
            )
        )

    def hot(self):
        """
        Returns a queryset of posts ordered by their calculated hot_score.
        Useful for 'Trending' or 'Front Page' feeds.
        """
        return self.annotate_hot_score().order_by("-hot_score")

    def new(self):
        """
        Returns a queryset ordered strictly by creation date.
        Useful for 'Latest' or 'Discovery' feeds.
        """
        return self.order_by("-created_at")
