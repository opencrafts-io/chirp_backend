from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.shortcuts import get_object_or_404
import os

from users.models import User


class GroupImage(models.Model):
    IMAGE_TYPE_CHOICES = [
        ("logo", "Logo"),
        ("banner", "Banner"),
    ]

    group = models.ForeignKey("Group", on_delete=models.CASCADE, related_name="images")
    image_type = models.CharField(
        max_length=10, choices=IMAGE_TYPE_CHOICES, default="logo"
    )
    file = models.ImageField(upload_to="groups/images/")
    file_size = models.BigIntegerField(null=True, blank=True)
    original_filename = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "image_type")

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
    GROUP_VISIBILITY_CHOICES = [
        ("public", "Public"),
        ("private", "Private"),
    ]
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="group_creators", null=True
    )
    visibility = models.CharField(
        max_length=20,
        choices=GROUP_VISIBILITY_CHOICES,
    )
    private = models.BooleanField(default=False)
    nsfw = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    guidelines = models.JSONField(default=list)
    member_count = models.PositiveIntegerField(default=0)
    moderator_count = models.PositiveIntegerField(default=0)
    banned_users_count = models.PositiveIntegerField(default=0)
    monthly_visitor_count = models.PositiveIntegerField(default=0)
    weekly_visitor_count = models.PositiveIntegerField(default=0)
    banner = models.ImageField(
        upload_to="groups/banners/",
        null=True,
        width_field="banner_width",
        height_field="banner_height",
    )
    banner_width = models.PositiveIntegerField(default=0)
    banner_height = models.PositiveIntegerField(default=0)
    profile_picture = models.ImageField(
        upload_to="groups/profile_pictures/",
        height_field="profile_picture_height",
        width_field="profile_picture_width",
        null=True,
    )
    profile_picture_height = models.PositiveIntegerField(default=0)
    profile_picture_width = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} created by ${self.creator}"

    def get_logo(self):
        """Get the logo image if it exists"""
        return GroupImage._default_manager.filter(group=self, image_type="logo").first()

    def get_banner(self):
        """Get the banner image if it exists"""
        return GroupImage._default_manager.filter(
            group=self, image_type="banner"
        ).first()

    def clean(self):
        """Custom validation for group model"""
        super().clean()

        if not self.name:
            raise ValidationError("Name is required.")

        if not self.creator:
            raise ValidationError("Creator is required.")

    def is_moderator(self, user_id: str) -> bool:
        """Check if user is a moderator of this group"""
        # Check if user is the creator
        if user_id == str(self.creator.user_id) if self.creator else False:
            return True

        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            return self.group_memberships.filter(user=user, role__in=["moderator", "creator"]).exists()
        except:
            return False

    def is_member(self, user_id: str) -> bool:
        """Check if user is a member of this group"""
        from users.models import User

        try:
            user = User._default_manager.get(user_id=user_id)
            return self.group_memberships.filter(
                user=user, role__in=["member", "moderator", "creator"]
            ).exists()
        except:
            return self.is_moderator(user_id)

    def can_view(self, user_id: str) -> bool:
        """Check if user can view this group"""
        if not self.private:
            return True
        return self.is_member(user_id)

    def can_post(self, user_id: str) -> bool:
        """Check if user can post in this group"""
        if not user_id:
            return False

        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            if self.group_memberships.filter(user=user, banned=True).exists():
                return False
        except:
            pass

        return self.is_member(user_id)

    def can_moderate(self, user_id: str) -> bool:
        """Check if user can moderate this group"""
        return self.is_moderator(user_id)

    def can_add_moderator(self) -> bool:
        """Check if more moderators can be added (under the 20 cap)"""
        moderator_count = self.group_memberships.filter(role__in=["moderator", "creator"]).count()
        if moderator_count >= 20:
            return False
        return True

    def add_moderator(self, user_id: str, user_name: str, added_by: str):
        """Add a moderator to the group (only existing moderators can do this)"""
        if not self.is_moderator(added_by):
            raise ValidationError("Only moderators can add other moderators")

        if not self.can_add_moderator():
            raise ValidationError(
                "Maximum number of moderators (20) reached for this group"
            )

        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            if not self.group_memberships.filter(user=user, role="moderator").exists() and user_id != str(self.creator.user_id) if self.creator else True:
                GroupMembership._default_manager.get_or_create(
                    group=self, user=user, defaults={"role": "moderator"}
                )
        except:
            pass

    def remove_moderator(self, user_id: str, removed_by: str):
        """Remove a moderator from the group (only creator can remove moderators)"""
        if removed_by != str(self.creator.user_id) if self.creator else True:
            raise ValidationError("Only the creator can remove moderators")

        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            if user_id != str(self.creator.user_id) if self.creator else True:
                membership = self.group_memberships.filter(user=user, role="moderator").first()
                if membership:
                    membership.delete()
        except:
            pass

    def add_member(self, user_id: str, user_name: str, added_by: str):
        """Add a member to the group (only admins/moderators can do this)"""
        if not self.is_moderator(added_by):
            raise ValidationError("Only moderators can add members")

        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            if not self.group_memberships.filter(user=user).exists() and not self.is_moderator(user_id):
                GroupMembership._default_manager.get_or_create(
                    group=self, user=user, defaults={"role": "member"}
                )
        except:
            pass

    def self_join(self, user_id: str, user_name: str):
        """Allow a user to join a public group themselves"""
        if self.private:
            raise ValidationError("Cannot self-join private groups")

        if self.is_member(user_id):
            raise ValidationError("Already a member of this group")

        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            if self.group_memberships.filter(user=user, banned=True).exists():
                raise ValidationError("You are banned from this group")

            GroupMembership._default_manager.get_or_create(
                group=self, user=user, defaults={"role": "member"}
            )
        except:
            pass

    def remove_member(self, user_id: str, removed_by: str):
        """Remove a member from the group (only admins/moderators can do this)"""
        if not self.is_moderator(removed_by):
            raise ValidationError("Only moderators can remove members")

        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            membership = self.group_memberships.filter(user=user, role="member").first()
            if membership:
                membership.delete()
        except:
            pass

    def ban_user(self, user_id: str, user_name: str, banned_by: str):
        """Ban a user from the group (only admins can do this)"""
        if not self.is_moderator(banned_by):
            raise ValidationError("Only moderators can ban users")

        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            membership = self.group_memberships.filter(user=user).first()
            if membership:
                membership.banned = True
                membership.save()
            else:
                GroupMembership._default_manager.create(
                    group=self, user=user, role="member", banned=True
                )
        except:
            pass

    def unban_user(self, user_id: str, unbanned_by: str):
        """Unban a user from the group (only admins can do this)"""
        if not self.is_moderator(unbanned_by):
            raise ValidationError("Only moderators can unban users")

        try:
            from users.models import User
            user = User.objects.get(user_id=user_id)
            membership = self.group_memberships.filter(user=user, banned=True).first()
            if membership:
                membership.banned = False
                membership.save()
        except:
            pass

    def add_rule(self, rule: str, added_by: str):
        """Add a rule to the community (only admins can do this)"""
        if not self.is_moderator(added_by):
            raise ValidationError("Only moderators can add community rules")

        if not rule or not rule.strip():
            raise ValidationError("Rule cannot be empty")

        current_rules = self.guidelines if isinstance(self.guidelines, list) else []
        if rule.strip() not in current_rules:
            current_rules.append(rule.strip())
            self.guidelines = current_rules
            self.save()

    def remove_rule(self, rule: str, removed_by: str):
        """Remove a rule from the community (only admins can do this)"""
        if not self.is_moderator(removed_by):
            raise ValidationError("Only moderators can remove community rules")

        current_rules = self.guidelines if isinstance(self.guidelines, list) else []
        if rule in current_rules:
            current_rules.remove(rule)
            self.guidelines = current_rules
            self.save()

    def update_rules(self, rules: list, updated_by: str):
        """Update all community rules (only admins can do this)"""
        if not self.is_moderator(updated_by):
            raise ValidationError("Only moderators can update community rules")

        if not isinstance(rules, list):
            raise ValidationError("Rules must be a list")

        valid_rules = [rule.strip() for rule in rules if rule and rule.strip()]

        self.guidelines = valid_rules
        self.save()

    def get_rules(self) -> list:
        """Get all community rules"""
        return self.guidelines if isinstance(self.guidelines, list) else []

    def get_user_list(self) -> dict:
        """Get a complete list of all users in the group with their names and roles"""
        memberships = self.group_memberships.all()

        moderators = []
        members = []
        banned = []

        for membership in memberships:
            user_data = {
                "user_id": str(membership.user.user_id),
                "name": membership.user.name,
                "role": membership.role
            }

            if membership.banned:
                banned.append(user_data)
            elif membership.role in ["moderator", "creator"]:
                moderators.append(user_data)
            else:
                members.append(user_data)
        return {
            "creator": {
                "user_id": str(self.creator.user_id) if self.creator else None,
                "name": self.creator.name if self.creator else None,
                "role": "creator",
            },
            "moderators": moderators,
            "members": members,
            "banned": banned,
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
        memberships = self.group_memberships.all()

        pass

        self.save()


class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ("moderator", "Moderator"),
        ("member", "Member"),
    ]

    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="group_memberships"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="group_members"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    banned = models.BooleanField(
        default=False,
    )
    banned_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="banned_memberships",
        null=True,
    )
    banning_reason = models.TextField(
        null=True,
        blank=True,
    )
    banned_at = models.DateTimeField(
        null=True,
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")
        indexes = [
            models.Index(fields=["group", "role"]),
            models.Index(fields=["user", "role"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.role} in {self.group.name}"


class GroupPost(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="posts")
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
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="invites")
    invitee_id = models.CharField(max_length=100)
    inviter_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Invitee to {self.group.name} for {self.invitee_id}"


class InviteLink(models.Model):
    """Model for community invite links"""

    EXPIRATION_CHOICES = [
        (72, "72 hours"),
        (168, "1 week"),
    ]

    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="invite_links"
    )
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
        db_table = "invite_links"

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
            self.expires_at = timezone.now() + timezone.timedelta(
                hours=self.expiration_hours
            )
        super().save(*args, **kwargs)
