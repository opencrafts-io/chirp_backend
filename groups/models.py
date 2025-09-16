from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.shortcuts import get_object_or_404
import os


class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ('creator', 'Creator'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
        ('banned', 'Banned'),
    ]

    group = models.ForeignKey('Group', on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')
        indexes = [
            models.Index(fields=['group', 'role']),
            models.Index(fields=['user', 'role']),
        ]

    def __str__(self):
        return f"{self.user} - {self.role} in {self.group.name}"


class GroupImage(models.Model):
    IMAGE_TYPE_CHOICES = [
        ("logo", "Logo"),
        ("banner", "Banner"),
    ]

    group = models.ForeignKey(
        "Group", on_delete=models.CASCADE, related_name="images"
    )
    image_type = models.CharField(
        max_length=10, choices=IMAGE_TYPE_CHOICES, default="logo"
    )
    file = models.ImageField(upload_to="groups/images/")
    file_size = models.BigIntegerField(null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'image_type')

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (OSError, ValueError):
                pass
        if self.file and not self.original_filename:
            try:
                self.original_filename = self.file.name
            except (OSError, ValueError):
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file:
            try:
                if os.path.isfile(self.file.path):
                    os.remove(self.file.path)
            except (OSError, ValueError):
                pass
        return super().delete(*args, **kwargs)

    def get_file_url(self):
        """Generate the full URL for the file"""
        if self.file:
            try:
                return self.file.url
            except (OSError, ValueError):
                return None
        return None

    def get_file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(float(str(self.file_size)) / (1024 * 1024), 2)
        return None

    def __str__(self):
        return f"{self.image_type} image for group {self.group.name}"


class Group(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    creator_id = models.CharField(max_length=100)
    creator_name = models.CharField(max_length=100, default='User')
    moderators = models.JSONField(default=list)
    moderator_names = models.JSONField(default=list)
    members = models.JSONField(default=list)
    member_names = models.JSONField(default=list)
    banned_users = models.JSONField(default=list)
    banned_user_names = models.JSONField(default=list)
    is_private = models.BooleanField(default=False)
    rules = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return str(self.name)

    def get_logo(self):
        """Get the logo image if it exists"""
        return GroupImage._default_manager.filter(group=self, image_type='logo').first()

    def get_banner(self):
        """Get the banner image if it exists"""
        return GroupImage._default_manager.filter(group=self, image_type='banner').first()

    def clean(self):
        """Custom validation for group model"""
        super().clean()

        if not self.name:
            raise ValidationError("Name is required.")

        if not self.creator_id:
            raise ValidationError("Creator ID is required.")

    def is_moderator(self, user_id: str) -> bool:
        """Check if user is a moderator of this group"""
        # Check if user is the creator
        if user_id == self.creator_id:
            return True

        # Check if user is in the moderators list
        moderators = self.moderators if isinstance(self.moderators, list) else []
        return user_id in moderators

    def is_member(self, user_id: str) -> bool:
        """Check if user is a member of this group"""
        from users.models import User
        try:
            user = User._default_manager.get(user_id=user_id)
            return self.memberships.filter(user=user, role__in=['member', 'moderator', 'creator']).exists()
        except:
            members = self.members if isinstance(self.members, list) else []
            return user_id in members or self.is_moderator(user_id)

    def can_view(self, user_id: str) -> bool:
        """Check if user can view this group"""
        if not self.is_private:
            return True
        return self.is_member(user_id)

    def can_post(self, user_id: str) -> bool:
        """Check if user can post in this group"""
        banned_users = self.banned_users if isinstance(self.banned_users, list) else []
        if user_id in banned_users:
            return False

        if not self.is_private:
            return True

        return self.is_member(user_id)

    def can_moderate(self, user_id: str) -> bool:
        """Check if user can moderate this group"""
        # Check if user is the creator
        if user_id == self.creator_id:
            return True

        # Check if user is in the moderators list
        moderators = self.moderators if isinstance(self.moderators, list) else []
        return user_id in moderators

    def can_add_moderator(self) -> bool:
        """Check if more moderators can be added (under the 20 cap)"""
        moderators = self.moderators if isinstance(self.moderators, list) else []
        if len(moderators) >= 20:
            return False
        return True

    def add_moderator(self, user_id: str, user_name: str, added_by: str):
        """Add a moderator to the group (only existing moderators can do this)"""
        if not self.is_moderator(added_by):
            raise ValidationError("Only moderators can add other moderators")

        if not self.can_add_moderator():
            raise ValidationError("Maximum number of moderators (20) reached for this group")

        current_moderators = self.moderators if isinstance(self.moderators, list) else []
        if user_id not in current_moderators and user_id != self.creator_id:
            current_moderator_names = self.moderator_names if isinstance(self.moderator_names, list) else []
            current_moderators.append(user_id)
            current_moderator_names.append(user_name)
            self.moderators = current_moderators
            self.moderator_names = current_moderator_names
            self.save()

            # Create GroupMembership record
            try:
                from users.models import User
                user = User.objects.get(user_id=user_id)
                GroupMembership.objects.get_or_create(
                    group=self,
                    user=user,
                    defaults={'role': 'moderator'}
                )
            except:
                pass

    def remove_moderator(self, user_id: str, removed_by: str):
        """Remove a moderator from the group (only creator can remove moderators)"""
        if removed_by != self.creator_id:
            raise ValidationError("Only the creator can remove moderators")

        current_moderators = self.moderators if isinstance(self.moderators, list) else []
        if user_id in current_moderators and user_id != self.creator_id:
            current_moderator_names = self.moderator_names if isinstance(self.moderator_names, list) else []
            index = current_moderators.index(user_id)
            current_moderators.remove(user_id)
            current_moderator_names.pop(index)
            self.moderators = current_moderators
            self.moderator_names = current_moderator_names
            self.save()

    def add_member(self, user_id: str, user_name: str, added_by: str):
        """Add a member to the group (only admins/moderators can do this)"""
        if not self.is_moderator(added_by):
            raise ValidationError("Only moderators can add members")

        current_members = self.members if isinstance(self.members, list) else []
        if user_id not in current_members and not self.is_moderator(user_id):
            current_member_names = self.member_names if isinstance(self.member_names, list) else []
            current_members.append(user_id)
            current_member_names.append(user_name)
            self.members = current_members
            self.member_names = current_member_names
            self.save()

            # Create GroupMembership record
            try:
                from users.models import User
                user = User.objects.get(user_id=user_id)
                GroupMembership.objects.get_or_create(
                    group=self,
                    user=user,
                    defaults={'role': 'member'}
                )
            except:
                pass

    def self_join(self, user_id: str, user_name: str):
        """Allow a user to join a public group themselves"""
        if self.is_private:
            raise ValidationError("Cannot self-join private groups")

        if self.is_member(user_id):
            raise ValidationError("Already a member of this group")

        current_banned = self.banned_users if isinstance(self.banned_users, list) else []
        if user_id in current_banned:
            raise ValidationError("You are banned from this group")

        current_members = self.members if isinstance(self.members, list) else []
        current_member_names = self.member_names if isinstance(self.member_names, list) else []

        current_members.append(user_id)
        current_member_names.append(user_name)
        self.members = current_members
        self.member_names = current_member_names
        self.save()

        # Create GroupMembership record
        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            GroupMembership.objects.get_or_create(
                group=self,
                user=user,
                defaults={'role': 'member'}
            )
        except:
            pass

    def remove_member(self, user_id: str, removed_by: str):
        """Remove a member from the group (only admins/moderators can do this)"""
        if not self.is_moderator(removed_by):
            raise ValidationError("Only moderators can remove members")

        current_members = self.members if isinstance(self.members, list) else []
        if user_id in current_members:
            current_member_names = self.member_names if isinstance(self.member_names, list) else []
            index = current_members.index(user_id)
            current_members.remove(user_id)
            current_member_names.pop(index)
            self.members = current_members
            self.member_names = current_member_names
            self.save()

            # Delete GroupMembership record
            try:
                from users.models import User
                user = User.objects.get(user_id=user_id)
                GroupMembership.objects.filter(group=self, user=user).delete()
            except:
                pass

    def ban_user(self, user_id: str, user_name: str, banned_by: str):
        """Ban a user from the group (only admins can do this)"""
        if not self.is_moderator(banned_by):
            raise ValidationError("Only moderators can ban users")

        current_banned = self.banned_users if isinstance(self.banned_users, list) else []
        if user_id not in current_banned:
            current_banned_names = self.banned_user_names if isinstance(self.banned_user_names, list) else []
            current_banned.append(user_id)
            current_banned_names.append(user_name)
            self.banned_users = current_banned
            self.banned_user_names = current_banned_names
            current_members = self.members if isinstance(self.members, list) else []
            if user_id in current_members:
                current_member_names = self.member_names if isinstance(self.member_names, list) else []
                index = current_members.index(user_id)
                current_members.remove(user_id)
                current_member_names.pop(index)
                self.members = current_members
                self.member_names = current_member_names

            current_moderators = self.moderators if isinstance(self.moderators, list) else []
            if user_id in current_moderators:
                current_moderator_names = self.moderator_names if isinstance(self.moderator_names, list) else []
                index = current_moderators.index(user_id)
                current_moderators.remove(user_id)
                current_moderator_names.pop(index)
                self.moderators = current_moderators
                self.moderator_names = current_moderator_names
            self.save()

            # Create GroupMembership record with banned role
            try:
                from users.models import User
                user = User.objects.get(user_id=user_id)
                GroupMembership.objects.get_or_create(
                    group=self,
                    user=user,
                    defaults={'role': 'banned'}
                )
            except:
                pass

    def unban_user(self, user_id: str, unbanned_by: str):
        """Unban a user from the group (only admins can do this)"""
        if not self.is_moderator(unbanned_by):
            raise ValidationError("Only moderators can unban users")

        current_banned = self.banned_users if isinstance(self.banned_users, list) else []
        current_banned_names = self.banned_user_names if isinstance(self.banned_user_names, list) else []
        if user_id in current_banned:
            index = current_banned.index(user_id)
            current_banned.remove(user_id)
            current_banned_names.pop(index)
            self.banned_users = current_banned
            self.banned_user_names = current_banned_names
            self.save()

            # Delete GroupMembership record
            try:
                from users.models import User
                user = User.objects.get(user_id=user_id)
                GroupMembership.objects.filter(group=self, user=user).delete()
            except:
                pass

    def add_rule(self, rule: str, added_by: str):
        """Add a rule to the community (only admins can do this)"""
        if not self.is_moderator(added_by):
            raise ValidationError("Only moderators can add community rules")

        if not rule or not rule.strip():
            raise ValidationError("Rule cannot be empty")

        current_rules = self.rules if isinstance(self.rules, list) else []
        if rule.strip() not in current_rules:
            current_rules.append(rule.strip())
            self.rules = current_rules
            self.save()

    def remove_rule(self, rule: str, removed_by: str):
        """Remove a rule from the community (only admins can do this)"""
        if not self.is_moderator(removed_by):
            raise ValidationError("Only moderators can remove community rules")

        current_rules = self.rules if isinstance(self.rules, list) else []
        if rule in current_rules:
            current_rules.remove(rule)
            self.rules = current_rules
            self.save()

    def update_rules(self, rules: list, updated_by: str):
        """Update all community rules (only admins can do this)"""
        if not self.is_moderator(updated_by):
            raise ValidationError("Only moderators can update community rules")

        if not isinstance(rules, list):
            raise ValidationError("Rules must be a list")

        valid_rules = [rule.strip() for rule in rules if rule and rule.strip()]

        self.rules = valid_rules
        self.save()

    def get_rules(self) -> list:
        """Get all community rules"""
        return self.rules if isinstance(self.rules, list) else []

    def get_user_list(self) -> dict:
        """Get a complete list of all users in the group with their names and roles"""
        current_moderators = self.moderators if isinstance(self.moderators, list) else []
        current_moderator_names = self.moderator_names if isinstance(self.moderator_names, list) else []
        current_members = self.members if isinstance(self.members, list) else []
        current_member_names = self.member_names if isinstance(self.member_names, list) else []
        current_banned = self.banned_users if isinstance(self.banned_users, list) else []
        current_banned_names = self.banned_user_names if isinstance(self.banned_user_names, list) else []
        return {
            'creator': {
                'user_id': self.creator_id,
                'user_name': self.creator_name,
                'role': 'creator'
            },
            'moderators': [
                {'user_id': user_id, 'user_name': name, 'role': 'moderator'}
                for user_id, name in zip(current_moderators, current_moderator_names)
            ],
            'members': [
                {'user_id': user_id, 'user_name': name, 'role': 'member'}
                for user_id, name in zip(current_members, current_member_names)
            ],
            'banned': [
                {'user_id': user_id, 'user_name': name, 'role': 'banned'}
                for user_id, name in zip(current_banned, current_banned_names)
            ]
        }

    def get_logo_url(self):
        """Get the URL for the community logo"""
        if self.get_logo():
            return self.get_logo().get_file_url()
        return None

    def get_banner_url(self):
        """Get the URL for the community banner"""
        if self.get_banner():
            return self.get_banner().get_file_url()
        return None

    def sync_json_fields(self):
        """Sync JSON fields with GroupMembership records for backward compatibility"""
        memberships = self.memberships.all()

        self.moderators = [m.user.user_id for m in memberships.filter(role='moderator')]
        self.moderator_names = [m.user.user_name for m in memberships.filter(role='moderator')]
        self.members = [m.user.user_id for m in memberships.filter(role='member')]
        self.member_names = [m.user.user_name for m in memberships.filter(role='member')]
        self.banned_users = [m.user.user_id for m in memberships.filter(role='banned')]
        self.banned_user_names = [m.user.user_name for m in memberships.filter(role='banned')]

        self.save()


class GroupPost(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='posts')
    user_id = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Custom validation for GroupPost model"""
        super().clean()

        if not self.content or not str(self.content).strip():
            raise ValidationError("Content cannot be empty")

        if not self.user_id or not str(self.user_id).strip():
            raise ValidationError("User ID cannot be empty")

    def __str__(self) -> str:
        return f"{self.user_id} in {self.group.name}: {self.content}..."


class GroupInvite(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invites')
    invitee_id = models.CharField(max_length=100)
    inviter_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Invitee to {self.group.name} for {self.invitee_id}"


class InviteLink(models.Model):
    """Model for community invite links"""

    EXPIRATION_CHOICES = [
        (72, '72 hours'),
        (168, '1 week'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invite_links')
    created_by = models.CharField(max_length=255)
    created_by_name = models.CharField(max_length=255)
    token = models.CharField(max_length=100, unique=True)
    expiration_hours = models.IntegerField(choices=EXPIRATION_CHOICES, default=72)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_by = models.CharField(max_length=255, null=True, blank=True)
    used_by_name = models.CharField(max_length=255, null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'invite_links'

    def __str__(self):
        return f"Invite to {self.group.name} (expires: {self.expires_at})"

    def is_expired(self):
        """Check if the invite link has expired"""
        return timezone.now() > self.expires_at

    def can_be_used(self):
        """Check if the invite link can be used"""
        return not self.is_used and not self.is_expired()

    def mark_as_used(self, user_id, user_name):
        """Mark the invite link as used"""
        self.is_used = True
        self.used_by = user_id
        self.used_by_name = user_name
        self.used_at = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        """Auto-calculate expiration time when saving"""
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=self.expiration_hours)
        super().save(*args, **kwargs)


