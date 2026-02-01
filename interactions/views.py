from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListCreateAPIView,
)
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import Block, Report
from .serializers import BlockSerializer, ReportSerializer
from users.models import User

class InteractionsBaseView:
    def get_user_from_ctx(self):
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            raise ValidationError({"error": "Failed to parse user information."})
        return User.objects.get(user_id=user_id)

class BlockToggleView(ListCreateAPIView, InteractionsBaseView):
    serializer_class = BlockSerializer

    def get_queryset(self):
        user = self.get_user_from_ctx()
        return Block.objects.filter(blocker=user)

    def perform_create(self, serializer):
        user = self.get_user_from_ctx()
        serializer.save(blocker=user)

class UnblockView(DestroyAPIView):
    """Handles unblocking a user or community."""
    queryset = Block.objects.all()
    lookup_field = 'id'

    def perform_destroy(self, instance):
        user_id = getattr(self.request, 'user_id', None)
        
        if str(instance.blocker.user_id) != str(user_id):
            raise PermissionDenied("You do not have permission to delete this block.")
            
        instance.delete()

class ReportCreateView(CreateAPIView, InteractionsBaseView):
    serializer_class = ReportSerializer

    def perform_create(self, serializer):
        user = self.get_user_from_ctx()
        serializer.save(reporter=user)