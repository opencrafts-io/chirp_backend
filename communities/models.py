from django.db import models
from django.utils import timezone

from users.models import User
from utils.uploads import get_community_banner_path, get_community_profile_path


class Community(models.Model):
    COMMUNITY_VISIBILITY_CHOICES = [
        ("public", "Public"),
        ("private", "Private"),
    ]
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="community_creators", null=True
    )
    visibility = models.CharField(
        max_length=20,
        choices=COMMUNITY_VISIBILITY_CHOICES,
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
        upload_to=get_community_banner_path,
        null=True,
        width_field="banner_width",
        height_field="banner_height",
    )
    banner_width = models.PositiveIntegerField(default=0)
    banner_height = models.PositiveIntegerField(default=0)
    profile_picture = models.ImageField(
        upload_to=get_community_profile_path,
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
        """
        Return a human-readable representation of the community combining its name and creator.

        Returns:
            str: A string formatted as "{name} created by ${creator}".
        """
        return f"{self.name} created by ${self.creator}"


class CommunityMembership(models.Model):
    ROLE_CHOICES = [
        ("super-mod", "Super Moderator"),
        ("moderator", "Moderator"),
        ("member", "Member"),
    ]

    community = models.ForeignKey(
        Community, on_delete=models.CASCADE, related_name="community_memberships"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="community_members"
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
        unique_together = ("community", "user")
        indexes = [
            models.Index(fields=["community", "role"]),
            models.Index(fields=["user", "role"]),
        ]

    def __str__(self):
        """
        Provide a human-readable string describing the membership's user, role, and community.

        Returns:
            A string formatted as "{user} - {role} in {community.name}".
        """
        return f"{self.user} - {self.role} in {self.community.name}"


class CommunityInvite(models.Model):
    community = models.ForeignKey(
        Community, on_delete=models.CASCADE, related_name="invites"
    )
    invitee_id = models.CharField(max_length=100)
    inviter_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """
        Provide a human-readable representation of the invite showing the community name and invitee identifier.

        Returns:
            A string containing the community name and invitee identifier in the format "Invitee to {community.name} for {invitee_id}".
        """
        return f"Invitee to {self.community.name} for {self.invitee_id}"


class InviteLink(models.Model):
    """Model for community invite links"""

    EXPIRATION_CHOICES = [
        (72, "72 hours"),
        (168, "1 week"),
    ]

    community = models.ForeignKey(
        Community, on_delete=models.CASCADE, related_name="invite_links"
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
        """
        Human-readable representation of the invite link.

        Returns:
            str: A string containing the community name and the invite's expiration datetime formatted as
                 "Invite to {community.name} (expires: {expires_at})".
        """
        return f"Invite to {self.community.name} (expires: {self.expires_at})"

    def is_expired(self):
        """
        Determine whether the invite link is past its expiration time.

        Returns:
            bool: True if the current time is after `expires_at`, False otherwise.
        """
        return timezone.now() > self.expires_at

    def can_be_used(self):
        """
        Determine whether the invite link is available for use.

        Returns:
            `true` if the link is not marked as used and has not expired, `false` otherwise.
        """
        return not self.is_used and not self.is_expired()

    def mark_as_used(self, user_id, user_name):
        """
        Mark this invite link as used and record the user and timestamp.

        Parameters:
            user_id (str): Identifier of the user who used the link.
            user_name (str): Display name of the user who used the link.
        """
        self.is_used = True
        self.used_by = user_id
        self.used_by_name = user_name
        self.used_at = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        """
        Ensure the invite link's expires_at is set from expiration_hours before saving.

        If `expires_at` is not set, set it to the current time plus `expiration_hours`, then perform the normal model save.
        """
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(
                hours=self.expiration_hours
            )
        super().save(*args, **kwargs)
