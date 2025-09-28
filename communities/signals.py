from django.db.models.signals import post_save, pre_save
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
