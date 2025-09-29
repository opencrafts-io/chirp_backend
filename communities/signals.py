from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from communities.models import CommunityMembership
from communities.views import Community


@receiver(post_save, sender=Community)
def create_owner_membership(sender, instance: Community, created: bool, **kwargs):
    """
    Create an initial super-mod CommunityMembership for a newly created Community.
    
    When a Community instance is created, create a CommunityMembership that links the community to its creator with the role "super-mod".
    
    Parameters:
        sender: The model class that sent the signal.
        instance (Community): The Community instance that was saved.
        created (bool): True if the Community instance was created (not just updated).
    """
    if created:
        CommunityMembership.objects.create(
            community=instance,
            role="super-mod",
            user=instance.creator,
        )


@receiver(post_save, sender=CommunityMembership)
def update_member_count_on_create(sender, instance, created, **kwargs):
    """
    Recalculate and persist a community's member, moderator, and banned user counts after a membership is created or when its role/banned status changes.
    
    Parameters:
        instance (CommunityMembership): The membership that triggered the signal; its associated community is used to recompute counts.
        created (bool): Whether the membership was newly created.
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
    Recomputes and persists a community's member, moderator, and banned-user counts after a membership is deleted.
    
    Updates:
    - member_count to the number of community memberships where `banned` is False.
    - moderator_count to the number of non-banned memberships whose `role` is "moderator" or "super-mod".
    - banned_users_count to the number of memberships where `banned` is True.
    Only the three updated fields are saved to the database.
    
    Parameters:
        instance (CommunityMembership): The membership instance that was deleted.
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
