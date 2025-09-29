from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from communities.models import CommunityMembership
from communities.views import Community


@receiver(post_save, sender=Community)
def create_owner_membership(sender, instance: Community, created: bool, **kwargs):
    if created:
        CommunityMembership.objects.create(
            community=instance,
            role="super-mod",
            user=instance.creator,
        )


@receiver(post_save, sender=CommunityMembership)
def update_member_count_on_create(sender, instance, created, **kwargs):
    """
    Increment counts when a membership is created or role changes.
    """
    community = instance.community

    # Update member count
    community.member_count = community.community_memberships.filter(
        banned=False
    ).count()

    # Update moderator count
    community.moderator_count = community.community_memberships.filter(
        role__in=["moderator", "super-mod"], banned=False
    ).count()

    # Update banned users count
    community.banned_users_count = community.community_memberships.filter(
        banned=True
    ).count()

    community.save(
        update_fields=["member_count", "moderator_count", "banned_users_count"]
    )


@receiver(post_delete, sender=CommunityMembership)
def update_member_count_on_delete(sender, instance, **kwargs):
    """
    Decrement counts when a membership is removed.
    """
    community = instance.community

    community.member_count = community.community_memberships.filter(
        banned=False
    ).count()
    community.moderator_count = community.community_memberships.filter(
        role__in=["moderator", "super-mod"], banned=False
    ).count()
    community.banned_users_count = community.community_memberships.filter(
        banned=True
    ).count()

    community.save(
        update_fields=["member_count", "moderator_count", "banned_users_count"]
    )
