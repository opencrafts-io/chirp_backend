from django.db import models
from django.core.exceptions import ValidationError


class Group(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    creator_id = models.CharField(max_length=100)
    admins = models.JSONField(default=list)
    moderators = models.JSONField(default=list)
    members = models.JSONField(default=list)
    banned_users = models.JSONField(default=list)
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.name

    def clean(self):
        """Custom validation for group model"""
        super().clean()

        if not self.name:
            raise ValidationError("Name is required.")

        if not self.creator_id:
            raise ValidationError("Creator ID is required.")

    def is_admin(self, user_id: str) -> bool:
        """Check if user is an admin of this group"""
        return user_id in self.admins or user_id == self.creator_id

    def is_moderator(self, user_id: str) -> bool:
        """Check if user is a moderator or admin of this group"""
        return user_id in self.moderators or self.is_admin(user_id)

    def is_member(self, user_id: str) -> bool:
        """Check if user is a member of this group"""
        return user_id in self.members or self.is_moderator(user_id)

    def can_view(self, user_id: str) -> bool:
        """Check if user can view this group"""
        if not self.is_private:
            return True
        return self.is_member(user_id)

    def can_post(self, user_id: str) -> bool:
        """Check if user can post in this group"""
        if user_id in self.banned_users:
            return False
        return self.is_member(user_id)

    def add_admin(self, user_id: str, added_by: str):
        """Add an admin to the group (only existing admins can do this)"""
        if not self.is_admin(added_by):
            raise ValidationError("Only admins can add other admins")

        if user_id not in self.admins and user_id != self.creator_id:
            current_admins = list(self.admins)
            current_admins.append(user_id)
            self.admins = current_admins
            self.save()

    def remove_admin(self, user_id: str, removed_by: str):
        """Remove an admin from the group (only creator can remove admins)"""
        if removed_by != self.creator_id:
            raise ValidationError("Only the creator can remove admins")

        if user_id in self.admins and user_id != self.creator_id:
            current_admins = list(self.admins)
            current_admins.remove(user_id)
            self.admins = current_admins
            self.save()

    def add_moderator(self, user_id: str, added_by: str):
        """Add a moderator to the group (only admins can do this)"""
        if not self.is_admin(added_by):
            raise ValidationError("Only admins can add moderators")

        if user_id not in self.moderators and not self.is_admin(user_id):
            current_moderators = list(self.moderators)
            current_moderators.append(user_id)
            self.moderators = current_moderators
            self.save()

    def remove_moderator(self, user_id: str, removed_by: str):
        """Remove a moderator from the group (only admins can do this)"""
        if not self.is_admin(removed_by):
            raise ValidationError("Only admins can remove moderators")

        if user_id in self.moderators:
            current_moderators = list(self.moderators)
            current_moderators.remove(user_id)
            self.moderators = current_moderators
            self.save()

    def add_member(self, user_id: str, added_by: str):
        """Add a member to the group (only admins/moderators can do this)"""
        if not self.is_moderator(added_by):
            raise ValidationError("Only admins/moderators can add members")

        if user_id not in self.members and not self.is_moderator(user_id):
            current_members = list(self.members)
            current_members.append(user_id)
            self.members = current_members
            self.save()

    def remove_member(self, user_id: str, removed_by: str):
        """Remove a member from the group (only admins/moderators can do this)"""
        if not self.is_moderator(removed_by):
            raise ValidationError("Only admins/moderators can remove members")

        if user_id in self.members:
            current_members = list(self.members)
            current_members.remove(user_id)
            self.members = current_members
            self.save()

    def ban_user(self, user_id: str, banned_by: str):
        """Ban a user from the group (only admins can do this)"""
        if not self.is_admin(banned_by):
            raise ValidationError("Only admins can ban users")

        if user_id not in self.banned_users:
            current_banned = list(self.banned_users)
            current_banned.append(user_id)
            self.banned_users = current_banned

            # Remove from members, moderators, and admins if they were in those roles
            if user_id in self.members:
                current_members = list(self.members)
                current_members.remove(user_id)
                self.members = current_members
            if user_id in self.moderators:
                current_moderators = list(self.moderators)
                current_moderators.remove(user_id)
                self.moderators = current_moderators
            if user_id in self.admins and user_id != self.creator_id:
                current_admins = list(self.admins)
                current_admins.remove(user_id)
                self.admins = current_admins
            self.save()

    def unban_user(self, user_id: str, unbanned_by: str):
        """Unban a user from the group (only admins can do this)"""
        if not self.is_admin(unbanned_by):
            raise ValidationError("Only admins can unban users")

        if user_id in self.banned_users:
            current_banned = list(self.banned_users)
            current_banned.remove(user_id)
            self.banned_users = current_banned
            self.save()


class GroupPost(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='posts')
    user_id = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user_id} in {self.group.name}: {self.content}..."


class GroupInvite(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invites')
    invitee_id = models.CharField(max_length=100)
    inviter_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Invitee to {self.group.name} for {self.invitee_id}"


