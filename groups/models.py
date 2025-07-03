from django.db import models

class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    creator_id = models.CharField(max_length=100)
    admins = models.JSONField(default=list)
    members = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroupPost(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='posts')
    user_id = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id} in {self.group.name}: {self.content}..."

class GroupInvite(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invites')
    invitee_id = models.CharField(max_length=100)
    inviter_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitee to {self.group.name} for {self.invitee_id}"


