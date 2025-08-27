from django.urls import path
from .views import MessageListCreateView, MessageDetailView, MessageReadView, MessageEditView, MessageDeleteView, ConversationMessageListView

urlpatterns = [
    path('', MessageListCreateView.as_view(), name='message-list-create'),
    path('<int:pk>/', MessageDetailView.as_view(), name='message-detail'),
    path('<int:pk>/read/', MessageReadView.as_view(), name='message-read'),
    path('<int:pk>/edit/', MessageEditView.as_view(), name='message-edit'),
    path('<int:pk>/', MessageDeleteView.as_view(), name='message-delete'),
    path('conversation/<str:conversation_id>/', ConversationMessageListView.as_view(), name='conversation-messages'),
]
