from django.urls import path
from .views import BlockToggleView, UnblockView, ReportCreateView

urlpatterns = [
    path('blocks/', BlockToggleView.as_view(), name='block-list-create'),
    path('unblocks/<int:id>/', UnblockView.as_view(), name='unblock'),
    path('reports/', ReportCreateView.as_view(), name='report-create'),
]