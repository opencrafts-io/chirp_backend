from django.urls import path
from . import views

app_name = 'websocket_chat'

urlpatterns = [
    path('conversations/<str:conversation_id>/upload/',
         views.FileUploadView.as_view(),
         name='file_upload'),
    path('conversations/<str:conversation_id>/messages/',
         views.ConversationMessagesHistoryView.as_view(),
         name='conversation_messages_history'),
    path('conversations/<str:conversation_id>/mark-read/',
         views.MarkMessagesAsReadView.as_view(),
         name='mark_messages_read'),
    path('conversations/<str:conversation_id>/info/',
         views.ConversationInfoView.as_view(),
         name='conversation_info'),
]
