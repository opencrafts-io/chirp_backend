from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import F
from posts.models import Post, PostView


@receiver(post_save, sender=PostView)
def increment_post_views_count(sender, instance: PostView, created: bool, **kwargs):
    if created:
        Post.objects.filter(id=instance.post.id).update(
            views_count=F("views_count") + 1
        )
