from django.urls import path
from .views import TweetsListCreateView

urlpatterns = [
    path('', TweetsListCreateView.as_view(), name='status-list-create'),
]
