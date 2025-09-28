from django.db import models
from django.utils import timezone

from users.models import User


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
