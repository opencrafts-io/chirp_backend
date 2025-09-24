from django.urls import path
from .views import LocalUserSearchView, UserListView, UserCountView


urlpatterns = [
    path('local/search/', LocalUserSearchView.as_view(), name='local_user_search'),
    path('count/', UserCountView.as_view(), name='user_count'),
    path('', UserListView.as_view(), name='user_list'),
]


