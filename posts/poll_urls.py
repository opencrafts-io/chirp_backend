from django.urls import path

from posts.views import PollVoteView, PollVotersListView

# Mounted at /polls/ (see chirp/urls.py).
urlpatterns = [
    path("<int:poll_id>/vote/", PollVoteView.as_view(), name="poll-vote"),
    path("<int:poll_id>/voters/", PollVotersListView.as_view(), name="poll-voters"),
]
