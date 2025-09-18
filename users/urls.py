from django.urls import path
from .views import LocalUserSearchView, UserListView


urlpatterns = [
    path('local/search/', LocalUserSearchView.as_view(), name='local_user_search'),
    path('', UserListView.as_view(), name='user_list'),
]


