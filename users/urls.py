from django.urls import path
from .views import LocalUserSearchView, UserListView, CreateUserView


urlpatterns = [
    path("register", CreateUserView.as_view(), name="register-user"),
    path("search", LocalUserSearchView.as_view(), name="local_user_search"),
    path("all", UserListView.as_view(), name="user_list"),
]
