from celery import shared_task
from celery.app.trace import logging

from communities.models import CommunityMembership
from event_bus.models.gossip_monger_notification_payload import (
    GOSSIP_MONGER_EXCHANGE,
    GOSSIP_MONGER_ROUTING_KEY,
    GossipMongerNotificationPayLoad,
)
from event_bus.publisher import publish
from posts.models import Comment, Post

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_push_notification_to_post_creator(self, post_id: int) -> None:
    """
    Sends a push notification to the author of a newly created post,
    prompting them to share it for engagement.

    Args:
        post_id: The primary key of the newly created Post.
    """
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        logger.error(
            f"Cannot send push notification: Post with id={post_id} not found."
        )
        return

    author_id = str(post.author_id)

    notification = GossipMongerNotificationPayLoad(
        headings={"en": "🎉 Your post is live!"},
        contents={
            "en": f"'{post.title}' is now in {post.community.name}. Share it to get your first 10 upvotes!"
        },
        subtitle={"en": "Success"},
        target_user_id=author_id,
        include_external_user_ids=[],
        buttons=[
            {"id": "view", "text": "View Post", "icon": "ic_visibility"},
        ],
        android_channel_id="60023d0b-dcd4-41ae-8e58-7eabbf382c8c",
        ios_sound="hangout",
        big_picture=None,
        large_icon=None,
        small_icon=None,
        url=f"https://academia.opencrafts.io/post/{post_id}",
    )

    try:
        publish(
            GOSSIP_MONGER_EXCHANGE, GOSSIP_MONGER_ROUTING_KEY, notification.to_json()
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3)
def send_push_notification_to_community_members(self, post_id: int) -> None:
    """
    Sends a push notification to all active, non-banned community members
    (excluding the post author) when a new post is created.
    Batches in groups of 2000 to respect OneSignal's limit.

    TODO: retrying this task re-publishes every batch, including ones that
    already succeeded, each with a fresh request_id. Since gossip-monger
    dedupes on request_id, a failure partway through resends duplicate
    notifications to earlier batches instead of a safe no-op. Fix by
    splitting into per-batch subtasks (or persisting request_ids per batch)
    if community sizes grow past a single 2000-member batch.

    Args:
        post_id: The primary key of the newly created Post.
    """
    try:
        post = Post.objects.select_related("author", "community").get(id=post_id)
    except Post.DoesNotExist:
        logger.error(
            f"Cannot send push notification: Post with id={post_id} not found."
        )
        return

    member_ids = (
        CommunityMembership.objects.filter(
            community=post.community,
            banned=False,
        )
        .exclude(user=post.author)
        .values_list("user__user_id", flat=True)
    )

    # Batch into chunks of 2000
    member_ids_list = [str(uid) for uid in member_ids]
    batch_size = 2000
    batches = [
        member_ids_list[i : i + batch_size]
        for i in range(0, len(member_ids_list), batch_size)
    ]

    for batch in batches:
        notification = GossipMongerNotificationPayLoad(
            headings={"en": f"New in a/{post.community.name}"},
            contents={"en": f"@{post.author.username}: {post.title}"},
            subtitle={"en": "Just now"},
            target_user_id=None,
            include_external_user_ids=batch,
            buttons=[
                {
                    "id": "view",
                    "text": "View Post",
                }
            ],
            android_channel_id="60023d0b-dcd4-41ae-8e58-7eabbf382c8c",
            ios_sound="hangout",
            big_picture=None,
            large_icon=(
                post.community.profile_picture.url
                if post.community.profile_picture
                else None
            ),
            small_icon=None,
            url=f"https://academia.opencrafts.io/post/{post_id}",
        )
        try:
            publish(
                GOSSIP_MONGER_EXCHANGE,
                GOSSIP_MONGER_ROUTING_KEY,
                notification.to_json(),
            )
        except Exception as exc:
            raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3)
def send_push_notification_to_post_author_on_comment(self, comment_id: int) -> None:
    """
    Notifies a post's author when someone else comments on their post.

    Skipped when the commenter is the post's author (no self-notify), or
    when this is a reply whose parent comment's author is also the post's
    author (send_push_notification_to_parent_comment_author_on_reply
    already reaches them in that case).

    Args:
        comment_id: The primary key of the newly created Comment.
    """
    try:
        comment = Comment.objects.select_related("author", "post", "parent").get(
            id=comment_id
        )
    except Comment.DoesNotExist:
        logger.error(
            f"Cannot send push notification: Comment with id={comment_id} not found."
        )
        return

    post = comment.post
    if comment.author_id == post.author_id:
        return
    if comment.parent is not None and comment.parent.author_id == post.author_id:
        return

    notification = GossipMongerNotificationPayLoad(
        headings={"en": "New comment"},
        contents={
            "en": f"@{comment.author.username} commented on your post: {comment.content[:100]}"
        },
        subtitle={"en": post.title or "Post"},
        target_user_id=str(post.author_id),
        include_external_user_ids=[],
        buttons=[
            {"id": "view", "text": "View Post", "icon": "ic_visibility"},
        ],
        android_channel_id="60023d0b-dcd4-41ae-8e58-7eabbf382c8c",
        ios_sound="hangout",
        big_picture=None,
        large_icon=None,
        small_icon=None,
        url=f"https://academia.opencrafts.io/post/{post.id}",
    )

    try:
        publish(
            GOSSIP_MONGER_EXCHANGE, GOSSIP_MONGER_ROUTING_KEY, notification.to_json()
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3)
def send_push_notification_to_parent_comment_author_on_reply(
    self, comment_id: int
) -> None:
    """
    Notifies a comment's author when someone else replies to their comment.

    No-op for top-level comments (no parent) or self-replies.

    Args:
        comment_id: The primary key of the newly created reply Comment.
    """
    try:
        comment = Comment.objects.select_related("author", "post", "parent").get(
            id=comment_id
        )
    except Comment.DoesNotExist:
        logger.error(
            f"Cannot send push notification: Comment with id={comment_id} not found."
        )
        return

    parent = comment.parent
    if parent is None or comment.author_id == parent.author_id:
        return

    post = comment.post
    notification = GossipMongerNotificationPayLoad(
        headings={"en": "New reply"},
        contents={
            "en": f"@{comment.author.username} replied to your comment: {comment.content[:100]}"
        },
        subtitle={"en": post.title or "Post"},
        target_user_id=str(parent.author_id),
        include_external_user_ids=[],
        buttons=[
            {"id": "view", "text": "View Post", "icon": "ic_visibility"},
        ],
        android_channel_id="60023d0b-dcd4-41ae-8e58-7eabbf382c8c",
        ios_sound="hangout",
        big_picture=None,
        large_icon=None,
        small_icon=None,
        url=f"https://academia.opencrafts.io/post/{post.id}",
    )

    try:
        publish(
            GOSSIP_MONGER_EXCHANGE, GOSSIP_MONGER_ROUTING_KEY, notification.to_json()
        )
    except Exception as exc:
        raise self.retry(exc=exc)
