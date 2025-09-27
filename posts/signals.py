from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db.models import F
from posts.models import Comment, Post, PostView


@receiver(post_save, sender=PostView)
def increment_post_views_count(sender, instance: PostView, created: bool, **kwargs):
    if created:
        Post.objects.filter(id=instance.post.id).update(
            views_count=F("views_count") + 1
        )


@receiver(pre_delete, sender=PostView)
def decrement_post_views_count(sender, instance: PostView, **kwargs):
    Post.objects.filter(id=instance.post.id).update(views_count=F("views_count") - 1)


@receiver(post_save, sender=Comment)
def increment_post_comment_count(sender, instance: Comment, created: bool, **kwargs):
    if created:
        Post.objects.filter(id=instance.post.id).update(
            comment_count=F("comment_count") + 1
        )


@receiver(pre_delete, sender=Comment)
def decrement_post_comment_count(sender, instance: Comment, **kwargs):
    Post.objects.filter(id=instance.post.id).update(
        comment_count=F("comment_count") - 1
    )
