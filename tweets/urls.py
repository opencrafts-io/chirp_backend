from django.urls import path
from .views import TweetsListCreateView, TweetReplyListCreateView

urlpatterns = [
    path('', TweetsListCreateView.as_view(), name='status-list-create'),
    path('<int:tweet_id>/replies/', TweetReplyListCreateView.as_view(), name='reply-list-create'),
]
