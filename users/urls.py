from django.urls import path
from .views import (
    LocalUserSearchView,
    UserListView,
    CreateUserView,
    UserRetrieveByIDApiView,
    UserRetrieveByUsernameApiView,
)


urlpatterns = [
    path("register", CreateUserView.as_view(), name="register-user"),
    path("search", LocalUserSearchView.as_view(), name="local_user_search"),
    path("all", UserListView.as_view(), name="user_list"),
    path(
        "find/<uuid:user_id>", UserRetrieveByIDApiView.as_view(), name="get-user-by-id"
    ),
    path(
        "who-is/<str:username>", UserRetrieveByUsernameApiView.as_view(), name="get-user-by-username"
    ),
]
