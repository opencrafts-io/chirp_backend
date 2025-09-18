from django.urls import path
from .views import LocalUserSearchView


urlpatterns = [
    path('search/', LocalUserSearchView.as_view(), name='local_user_search'),
]


