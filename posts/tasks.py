from celery import shared_task
from celery.app.trace import logging

from communities.models import CommunityMembership
from event_bus.models.gossip_monger_notification_payload import (
    GOSSIP_MONGER_EXCHANGE,
    GOSSIP_MONGER_ROUTING_KEY,
    GossipMongerNotificationPayLoad,
)
from event_bus.publisher import publish
from posts.models import Post

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

    publish(GOSSIP_MONGER_EXCHANGE, GOSSIP_MONGER_ROUTING_KEY, notification.to_json())


@shared_task(bind=True)
def send_push_notification_to_community_members(self, post_id: int) -> None:
    """
    Sends a push notification to all active, non-banned community members
    (excluding the post author) when a new post is created.
    Batches in groups of 2000 to respect OneSignal's limit.

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
        publish(
            GOSSIP_MONGER_EXCHANGE, GOSSIP_MONGER_ROUTING_KEY, notification.to_json()
        )
