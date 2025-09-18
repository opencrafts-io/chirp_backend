from django.urls import path
from .views import LocalUserSearchView


urlpatterns = [
    path('local/search/', LocalUserSearchView.as_view(), name='local_user_search'),
]


