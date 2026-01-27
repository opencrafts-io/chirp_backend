from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
from posts.models import Post
from communities.models import Community

class Block(models.Model):
    BLOCK_TYPES = [
        ('user', 'User'),
        ('community', 'Community'),
    ]
    
    blocker = models.ForeignKey(User, related_name='blocking_relations', on_delete=models.CASCADE)
    blocked_user = models.ForeignKey(User, related_name='blocked_by_relations', on_delete=models.CASCADE, null=True, blank=True)
    blocked_community = models.ForeignKey(Community, related_name='blocked_by_relations', on_delete=models.CASCADE, null=True, blank=True)
    
    block_type = models.CharField(max_length=10, choices=BLOCK_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked_user', 'block_type')

    def clean(self):
        if self.block_type == 'user' and not self.blocked_user:
            raise ValidationError("A user must be specified for user-type blocks.")
        if self.block_type == 'community' and not self.blocked_community:
            raise ValidationError("A community must be specified for community-type blocks.")
        if self.blocked_user and self.blocker == self.blocked_user:
            raise ValidationError("You cannot block yourself.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Report(models.Model):
    REPORT_TYPES = [
        ('user', 'User'),
        ('post', 'Post'),
        ('comment', 'Comment'),
        ('community', 'Community'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    reporter = models.ForeignKey(User, related_name='reports_sent', on_delete=models.CASCADE)
    reported_user = models.ForeignKey(User, related_name='reports_received', on_delete=models.CASCADE, null=True, blank=True)
    reported_post = models.ForeignKey(Post, related_name='reports', null=True, blank=True, on_delete=models.SET_NULL)
    reported_comment = models.ForeignKey('posts.Comment', related_name='reports', null=True, blank=True, on_delete=models.SET_NULL)
    reported_community = models.ForeignKey(Community, related_name='reports', null=True, blank=True, on_delete=models.SET_NULL)
    
    report_type = models.CharField(max_length=10, choices=REPORT_TYPES)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    reviewed_by = models.ForeignKey(User, related_name='reports_reviewed', null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    moderator_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)