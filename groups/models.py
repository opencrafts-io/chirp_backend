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
    creator_name = models.CharField(max_length=100, default='User')
    admins = models.JSONField(default=list)
    admin_names = models.JSONField(default=list)
    moderators = models.JSONField(default=list)
    moderator_names = models.JSONField(default=list)
    members = models.JSONField(default=list)
    member_names = models.JSONField(default=list)
    banned_users = models.JSONField(default=list)
    banned_user_names = models.JSONField(default=list)
    is_private = models.BooleanField(default=False)
    rules = models.JSONField(default=list)
    logo = models.ImageField(upload_to='groups/logos/', null=True, blank=True, help_text='Community logo (square image recommended)')
    banner = models.ImageField(upload_to='groups/banners/', null=True, blank=True, help_text='Community banner image (wide image recommended)')

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

    def add_admin(self, user_id: str, user_name: str, added_by: str):
        """Add an admin to the group (only existing admins can do this)"""
        if not self.is_admin(added_by):
            raise ValidationError("Only admins can add other admins")

        if user_id not in self.admins and user_id != self.creator_id:
            current_admins = list(self.admins)
            current_admin_names = list(self.admin_names)
            current_admins.append(user_id)
            current_admin_names.append(user_name)
            self.admins = current_admins
            self.admin_names = current_admin_names
            self.save()

    def remove_admin(self, user_id: str, removed_by: str):
        """Remove an admin from the group (only creator can remove admins)"""
        if removed_by != self.creator_id:
            raise ValidationError("Only the creator can remove admins")

        if user_id in self.admins and user_id != self.creator_id:
            current_admins = list(self.admins)
            current_admin_names = list(self.admin_names)
            index = current_admins.index(user_id)
            current_admins.remove(user_id)
            current_admin_names.pop(index)
            self.admins = current_admins
            self.admin_names = current_admin_names
            self.save()

    def add_moderator(self, user_id: str, user_name: str, added_by: str):
        """Add a moderator to the group (only admins can do this)"""
        if not self.is_admin(added_by):
            raise ValidationError("Only admins can add moderators")

        if user_id not in self.moderators and not self.is_admin(user_id):
            current_moderators = list(self.moderators)
            current_moderator_names = list(self.moderator_names)
            current_moderators.append(user_id)
            current_moderator_names.append(user_name)
            self.moderators = current_moderators
            self.moderator_names = current_moderator_names
            self.save()

    def remove_moderator(self, user_id: str, removed_by: str):
        """Remove a moderator from the group (only admins can do this)"""
        if not self.is_admin(removed_by):
            raise ValidationError("Only admins can remove moderators")

        if user_id in self.moderators:
            current_moderators = list(self.moderators)
            current_moderator_names = list(self.moderator_names)
            index = current_moderators.index(user_id)
            current_moderators.remove(user_id)
            current_moderator_names.pop(index)
            self.moderators = current_moderators
            self.moderator_names = current_moderator_names
            self.save()

    def add_member(self, user_id: str, user_name: str, added_by: str):
        """Add a member to the group (only admins/moderators can do this)"""
        if not self.is_moderator(added_by):
            raise ValidationError("Only admins/moderators can add members")

        if user_id not in self.members and not self.is_moderator(user_id):
            current_members = list(self.members)
            current_member_names = list(self.member_names)
            current_members.append(user_id)
            current_member_names.append(user_name)
            self.members = current_members
            self.member_names = current_member_names
            self.save()

    def remove_member(self, user_id: str, removed_by: str):
        """Remove a member from the group (only admins/moderators can do this)"""
        if not self.is_moderator(removed_by):
            raise ValidationError("Only admins/moderators can remove members")

        if user_id in self.members:
            current_members = list(self.members)
            current_member_names = list(self.member_names)
            index = current_members.index(user_id)
            current_members.remove(user_id)
            current_member_names.pop(index)
            self.members = current_members
            self.member_names = current_member_names
            self.save()

    def ban_user(self, user_id: str, user_name: str, banned_by: str):
        """Ban a user from the group (only admins can do this)"""
        if not self.is_admin(banned_by):
            raise ValidationError("Only admins can ban users")

        if user_id not in self.banned_users:
            current_banned = list(self.banned_users)
            current_banned_names = list(self.banned_user_names)
            current_banned.append(user_id)
            current_banned_names.append(user_name)
            self.banned_users = current_banned
            self.banned_user_names = current_banned_names

            # Remove from members, moderators, and admins if they were in those roles
            if user_id in self.members:
                current_members = list(self.members)
                current_member_names = list(self.member_names)
                index = current_members.index(user_id)
                current_members.remove(user_id)
                current_member_names.pop(index)
                self.members = current_members
                self.member_names = current_member_names

            if user_id in self.moderators:
                current_moderators = list(self.moderators)
                current_moderator_names = list(self.moderator_names)
                index = current_moderators.index(user_id)
                current_moderators.remove(user_id)
                current_moderator_names.pop(index)
                self.moderators = current_moderators
                self.moderator_names = current_moderator_names

            if user_id in self.admins and user_id != self.creator_id:
                current_admins = list(self.admins)
                current_admin_names = list(self.admin_names)
                index = current_admins.index(user_id)
                current_admins.remove(user_id)
                current_admin_names.pop(index)
                self.admins = current_admins
                self.admin_names = current_admin_names
            self.save()

    def unban_user(self, user_id: str, unbanned_by: str):
        """Unban a user from the group (only admins can do this)"""
        if not self.is_admin(unbanned_by):
            raise ValidationError("Only admins can unban users")

        if user_id in self.banned_users:
            current_banned = list(self.banned_users)
            current_banned_names = list(self.banned_user_names)
            index = current_banned.index(user_id)
            current_banned.remove(user_id)
            current_banned_names.pop(index)
            self.banned_users = current_banned
            self.banned_user_names = current_banned_names
            self.save()

    def add_rule(self, rule: str, added_by: str):
        """Add a rule to the community (only admins can do this)"""
        if not self.is_admin(added_by):
            raise ValidationError("Only admins can add community rules")

        if not rule or not rule.strip():
            raise ValidationError("Rule cannot be empty")

        current_rules = list(self.rules)
        if rule.strip() not in current_rules:
            current_rules.append(rule.strip())
            self.rules = current_rules
            self.save()

    def remove_rule(self, rule: str, removed_by: str):
        """Remove a rule from the community (only admins can do this)"""
        if not self.is_admin(removed_by):
            raise ValidationError("Only admins can remove community rules")

        current_rules = list(self.rules)
        if rule in current_rules:
            current_rules.remove(rule)
            self.rules = current_rules
            self.save()

    def update_rules(self, rules: list, updated_by: str):
        """Update all community rules (only admins can do this)"""
        if not self.is_admin(updated_by):
            raise ValidationError("Only admins can update community rules")

        # Validate rules
        if not isinstance(rules, list):
            raise ValidationError("Rules must be a list")

        # Filter out empty rules
        valid_rules = [rule.strip() for rule in rules if rule and rule.strip()]

        self.rules = valid_rules
        self.save()

    def get_rules(self) -> list:
        """Get all community rules"""
        return list(self.rules) if self.rules else []

    def get_user_list(self) -> dict:
        """Get a complete list of all users in the group with their names and roles"""
        return {
            'creator': {
                'user_id': self.creator_id,
                'user_name': self.creator_name,
                'role': 'creator'
            },
            'admins': [
                {'user_id': user_id, 'user_name': name, 'role': 'admin'}
                for user_id, name in zip(self.admins, self.admin_names)
            ],
            'moderators': [
                {'user_id': user_id, 'user_name': name, 'role': 'moderator'}
                for user_id, name in zip(self.moderators, self.moderator_names)
            ],
            'members': [
                {'user_id': user_id, 'user_name': name, 'role': 'member'}
                for user_id, name in zip(self.members, self.member_names)
            ],
            'banned': [
                {'user_id': user_id, 'user_name': name, 'role': 'banned'}
                for user_id, name in zip(self.banned_users, self.banned_user_names)
            ]
        }

    def get_logo_url(self):
        """Get the URL for the community logo"""
        if self.logo:
            return self.logo.url
        return None

    def get_banner_url(self):
        """Get the URL for the community banner"""
        if self.banner:
            return self.banner.url
        return None


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


