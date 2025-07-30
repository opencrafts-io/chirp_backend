from django.urls import path
from . import views

app_name = 'conversations'

urlpatterns = [
    path('', views.ConversationListView.as_view(), name='conversation-list'),
    path('create/', views.ConversationCreateView.as_view(), name='conversation-create'),
    path('<str:conversation_id>/messages/', views.ConversationMessagesView.as_view(), name='conversation-messages'),
    path('<str:conversation_id>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
]