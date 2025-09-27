from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db.models import F
from posts.models import Comment, Post, PostView, PostVotes


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


@receiver(post_save, sender=PostVotes)
def update_post_vote_counts(sender, instance: PostVotes, created: bool, **kwargs):
    """
    Increment or update the vote counts on the related post.
    """
    post = instance.post
    if created:
        # New vote
        if instance.value == PostVotes.UPVOTE:
            Post.objects.filter(id=post.id).update(upvotes=F("upvotes") + 1)
        elif instance.value == PostVotes.DOWNVOTE:
            Post.objects.filter(id=post.id).update(downvotes=F("downvotes") + 1)
    else:
        # Vote updated: recalc the counts to stay accurate
        upvotes = PostVotes.objects.filter(post=post, value=PostVotes.UPVOTE).count()
        downvotes = PostVotes.objects.filter(
            post=post, value=PostVotes.DOWNVOTE
        ).count()
        Post.objects.filter(id=post.id).update(upvotes=upvotes, downvotes=downvotes)


@receiver(pre_delete, sender=PostVotes)
def decrement_post_vote_counts(sender, instance: PostVotes, **kwargs):
    """
    Decrement the vote count when a vote is removed.
    """
    post = instance.post
    if instance.value == PostVotes.UPVOTE:
        Post.objects.filter(id=post.id).update(upvotes=F("upvotes") - 1)
    elif instance.value == PostVotes.DOWNVOTE:
        Post.objects.filter(id=post.id).update(downvotes=F("downvotes") - 1)
