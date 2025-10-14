from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db.models import F
from posts.models import Comment, Post, PostView, PostVotes


@receiver(post_save, sender=PostView)
def increment_post_views_count(sender, instance: PostView, created: bool, **kwargs):
    """
    Increment the related Post's views_count when a new PostView is created.
    
    Parameters:
    	instance (PostView): The PostView instance that triggered the signal.
    	created (bool): True if the PostView was newly created.
    """
    if created:
        Post.objects.filter(id=instance.post.id).update(
            views_count=F("views_count") + 1
        )


@receiver(pre_delete, sender=PostView)
def decrement_post_views_count(sender, instance: PostView, **kwargs):
    """
    Decrements the related Post's views_count by 1 when a PostView is deleted.
    
    Parameters:
        sender: The model class sending the signal.
        instance (PostView): The PostView instance about to be deleted.
    """
    Post.objects.filter(id=instance.post.id).update(views_count=F("views_count") - 1)


@receiver(post_save, sender=Comment)
def increment_post_comment_count(sender, instance: Comment, created: bool, **kwargs):
    """
    Increment a post's comment_count when a new Comment is created.
    
    If the saved Comment was newly created, atomically increments the related Post's comment_count by 1.
    
    Parameters:
        instance (Comment): The Comment instance that was saved.
        created (bool): True if the Comment was newly created, False if it was an update.
    """
    if created:
        Post.objects.filter(id=instance.post.id).update(
            comment_count=F("comment_count") + 1
        )


@receiver(pre_delete, sender=Comment)
def decrement_post_comment_count(sender, instance: Comment, **kwargs):
    """
    Decrement the associated Post's comment_count by one when a Comment is removed.
    
    Parameters:
        instance (Comment): The Comment instance being deleted; its related Post's comment_count will be decremented.
    """
    Post.objects.filter(id=instance.post.id).update(
        comment_count=F("comment_count") - 1
    )


@receiver(post_save, sender=PostVotes)
def update_post_vote_counts(sender, instance: PostVotes, created: bool, **kwargs):
    """
    Maintain the related Post's upvote and downvote counts when a PostVotes record is created or updated.
    
    If `created` is True, increment the post's upvote or downvote counter depending on the vote value. If `created` is False, recalculate both upvote and downvote counts from PostVotes and write them to the Post.
    
    Parameters:
        sender: The model class that sent the signal (ignored by this function).
        instance (PostVotes): The vote instance that was created or updated.
        created (bool): True if the `instance` was newly created, False if it was updated.
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
    Decrement the corresponding Post vote counter when a PostVotes instance is deleted.
    
    If the removed vote is an upvote, decrement the Post.upvotes counter; if it's a downvote, decrement the Post.downvotes counter.
    """
    post = instance.post
    if instance.value == PostVotes.UPVOTE:
        Post.objects.filter(id=post.id).update(upvotes=F("upvotes") - 1)
    elif instance.value == PostVotes.DOWNVOTE:
        Post.objects.filter(id=post.id).update(downvotes=F("downvotes") - 1)
